"""
Webhook endpoint — Composio's project-wide webhook subscription POSTs every
project event here (trigger messages, connection-expiry, etc.), signed with
its own HMAC scheme. We verify the signature, then only act on
composio.trigger.message events from the Gmail poll-trigger
(GMAIL_NEW_GMAIL_MESSAGE, filtered to from:noreplyubi-txn@ubi.bank.in) —
everything else is acknowledged and ignored.

See https://docs.composio.dev/docs/setting-up-triggers/subscribing-to-events
"""
import json

from fastapi import APIRouter, Header, HTTPException, Request

from config import COMPOSIO_WEBHOOK_SECRET, TELEGRAM_ALLOWED_ID
from services.email_ingest import process_debit_email
from utils.composio_webhook import extract_trigger_slug, verify_composio_signature

router = APIRouter(prefix="/email", tags=["email"])

GMAIL_TRIGGER_SLUG = "GMAIL_NEW_GMAIL_MESSAGE"

# Composio's `query` filter already restricts polling to this sender, but a
# mis-scoped filter (or a future Composio config change) shouldn't be able
# to feed arbitrary mail into the money path — this is cheap defense-in-depth
# on top of the signature check.
EXPECTED_SENDER = "noreplyubi-txn@ubi.bank.in"


@router.post("/webhook")
async def email_webhook(
    request: Request,
    webhook_id: str = Header(default=""),
    webhook_timestamp: str = Header(default=""),
    webhook_signature: str = Header(default=""),
):
    raw_body = await request.body()
    if not verify_composio_signature(
        COMPOSIO_WEBHOOK_SECRET, webhook_id, webhook_timestamp, raw_body, webhook_signature
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        envelope = json.loads(raw_body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if extract_trigger_slug(envelope) != GMAIL_TRIGGER_SLUG:
        # Some other project event (connection expiry, a different trigger,
        # etc.) — acknowledge, nothing to do here.
        return {"ok": True, "reason": "ignored_event"}

    data = envelope.get("data") or {}
    sender = data.get("sender", "")
    if EXPECTED_SENDER not in sender:
        return {"ok": False, "reason": "unexpected_sender"}

    message_text = data.get("message_text", "")
    subject = data.get("subject", "")

    pool = request.app.state.pool
    bot = request.app.state.telegram_app.bot
    result = await process_debit_email(
        pool, bot, TELEGRAM_ALLOWED_ID, message_text, subject
    )
    return result
