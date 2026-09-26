"""
Gmail push ingestion: Gmail -> Cloud Pub/Sub -> POST /email/gmail-push -> sync().

Pub/Sub only says "the mailbox changed" (a historyId), so sync() pulls the
actual new messages via history.list from the cursor stored in gmail_sync,
and hands each bank alert to process_debit_email(). The watch covers a single
Gmail label (a Gmail filter files the bank's alerts under it) and expires
after 7 days, so /cron/gmail-watch renews it daily and catches up on any
notification Pub/Sub dropped.

See https://developers.google.com/workspace/gmail/api/guides/push
"""
import asyncio
import base64
from contextlib import asynccontextmanager

import httpx

from config import (
    GMAIL_CLIENT_ID,
    GMAIL_CLIENT_SECRET,
    GMAIL_LABEL_ID,
    GMAIL_PUBSUB_TOPIC,
    GMAIL_REFRESH_TOKEN,
)
from db.queries import get_gmail_history_id, set_gmail_history_id
from services.email_ingest import process_debit_email
from utils.email_parser import BANK_SENDERS

API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# The Gmail filter already scopes the label to these senders, but a mis-set
# filter shouldn't be able to feed arbitrary mail into the money path.

# ponytail: in-process lock — fine for the single Render instance; switch to a
# pg advisory lock if the API ever runs more than one instance.
_sync_lock = asyncio.Lock()


def is_configured() -> bool:
    return all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_PUBSUB_TOPIC, GMAIL_LABEL_ID])


@asynccontextmanager
async def _gmail():
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, data={
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "refresh_token": GMAIL_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        })
        r.raise_for_status()
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        yield client


def extract_body(payload: dict) -> str:
    """Decoded body of a Gmail API message payload — text/html preferred (what
    the parser was built against), falling back to text/plain."""
    found: dict[str, str] = {}

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        data = (part.get("body") or {}).get("data")
        if data and mime in ("text/html", "text/plain") and mime not in found:
            found[mime] = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
        for child in part.get("parts") or []:
            walk(child)

    walk(payload)
    return found.get("text/html") or found.get("text/plain", "")


def header(payload: dict, name: str) -> str:
    for h in payload.get("headers") or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


async def sync(pool, bot, chat_id: int) -> dict:
    """Process every bank alert added to the label since the stored cursor.
    Safe to re-run: the RRN unique key makes reprocessing a no-op."""
    async with _sync_lock:
        start = await get_gmail_history_id(pool)
        if start is None:
            return {"ok": False, "reason": "watch_not_started"}

        async with _gmail() as client:
            message_ids: list[str] = []
            latest = start
            page_token = None
            while True:
                params = {"startHistoryId": start, "historyTypes": "messageAdded", "labelId": GMAIL_LABEL_ID}
                if page_token:
                    params["pageToken"] = page_token
                r = await client.get(f"{API}/history", params=params)
                if r.status_code == 404:
                    # Cursor is older than Gmail keeps history (~1 week) — only
                    # possible if push AND the daily cron were down that long.
                    profile = (await client.get(f"{API}/profile")).json()
                    await set_gmail_history_id(pool, int(profile["historyId"]))
                    await bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ Gmail sync was down for over a week — check your bank alerts from that period and log any missing ones manually.",
                    )
                    return {"ok": False, "reason": "history_expired"}
                r.raise_for_status()
                body = r.json()
                for entry in body.get("history", []):
                    message_ids += [m["message"]["id"] for m in entry.get("messagesAdded", [])]
                latest = int(body["historyId"])
                page_token = body.get("nextPageToken")
                if not page_token:
                    break

            results = []
            for message_id in dict.fromkeys(message_ids):
                r = await client.get(f"{API}/messages/{message_id}", params={"format": "full"})
                if r.status_code == 404:
                    continue  # deleted before we got to it
                r.raise_for_status()
                payload = r.json()["payload"]
                sender = header(payload, "From")
                if not any(bank in sender for bank in BANK_SENDERS):
                    continue
                results.append(await process_debit_email(
                    pool, bot, chat_id, extract_body(payload), header(payload, "Subject"), sender
                ))

        # Only advance once everything is handled — a crash above leaves the
        # cursor put, and Pub/Sub's retry picks the same messages up again.
        await set_gmail_history_id(pool, latest)
        return {"ok": True, "results": results}


async def renew_watch(pool, bot, chat_id: int) -> dict:
    """Daily: catch up on anything push missed, then renew the 7-day watch.
    The first run also sets the starting cursor."""
    synced = await sync(pool, bot, chat_id)
    async with _gmail() as client:
        r = await client.post(f"{API}/watch", json={
            "topicName": GMAIL_PUBSUB_TOPIC,
            "labelIds": [GMAIL_LABEL_ID],
            "labelFilterBehavior": "INCLUDE",
        })
        r.raise_for_status()
        watch = r.json()
    if synced.get("reason") == "watch_not_started":
        await set_gmail_history_id(pool, int(watch["historyId"]))
    return {"ok": True, "expiration": watch["expiration"], "sync": synced}
