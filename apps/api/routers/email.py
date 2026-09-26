"""
Gmail push endpoint — Cloud Pub/Sub POSTs here whenever the watched Gmail
label changes. The notification only carries a historyId, so its body is
ignored and sync() pulls whatever is new since our stored cursor.

Pub/Sub push can't sign requests with a shared secret, so the subscription's
push URL carries ?token=<GMAIL_PUSH_TOKEN>.
"""
import hmac

from fastapi import APIRouter, HTTPException, Request

from config import GMAIL_PUSH_TOKEN, TELEGRAM_ALLOWED_ID
from services import gmail_sync

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/gmail-push")
async def gmail_push(request: Request, token: str = ""):
    if not GMAIL_PUSH_TOKEN or not hmac.compare_digest(token, GMAIL_PUSH_TOKEN):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not gmail_sync.is_configured():
        raise HTTPException(status_code=503, detail="Gmail ingestion not configured")

    # Any exception here becomes a 500, so Pub/Sub retries — sync() is
    # idempotent, and the cursor only advances after a clean run.
    return await gmail_sync.sync(
        request.app.state.pool, request.app.state.telegram_app.bot, TELEGRAM_ALLOWED_ID
    )
