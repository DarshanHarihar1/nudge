"""
Webhook endpoint — Composio's Gmail poll-trigger (GMAIL_NEW_GMAIL_MESSAGE,
filtered to from:noreplyubi-txn@ubi.bank.in) POSTs new-message events here.

Auth: shared secret header (X-Webhook-Secret), same pattern as Telegram's
own webhook secret header in main.py.
"""
from fastapi import APIRouter, Header, HTTPException, Request

from config import EMAIL_WEBHOOK_SECRET, TELEGRAM_ALLOWED_ID
from services.email_ingest import process_debit_email

router = APIRouter(prefix="/email", tags=["email"])

# Composio's `query` filter already restricts polling to this sender, but a
# mis-scoped filter (or a future Composio config change) shouldn't be able
# to feed arbitrary mail into the money path — the shared secret is the
# real control, this is cheap defense-in-depth on top of it.
EXPECTED_SENDER = "noreplyubi-txn@ubi.bank.in"


@router.post("/webhook")
async def email_webhook(
    request: Request,
    x_webhook_secret: str = Header(default=""),
):
    if not EMAIL_WEBHOOK_SECRET or x_webhook_secret != EMAIL_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()
    sender = body.get("sender", "")
    if EXPECTED_SENDER not in sender:
        return {"ok": False, "reason": "unexpected_sender"}

    message_text = body.get("message_text", "")
    subject = body.get("subject", "")

    pool = request.app.state.pool
    bot = request.app.state.telegram_app.bot
    result = await process_debit_email(
        pool, bot, TELEGRAM_ALLOWED_ID, message_text, subject
    )
    return result
