"""
Cron endpoints — all require Authorization: Bearer <CRON_SECRET>.
Called by GitHub Actions on schedule.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import CRON_SECRET, TELEGRAM_ALLOWED_ID
from services.recurring import apply_recurring_items

router = APIRouter(prefix="/cron", tags=["cron"])
_bearer = HTTPBearer()


def _verify_secret(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    if creds.credentials != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── apply-recurring ───────────────────────────────────────────────────────────

@router.post("/apply-recurring", dependencies=[Depends(_verify_secret)])
async def cron_apply_recurring(request: Request):
    """Daily 00:05 IST — apply recurring items due today."""
    pool = request.app.state.pool
    bot = request.app.state.telegram_app.bot
    result = await apply_recurring_items(pool, bot, TELEGRAM_ALLOWED_ID)
    return {"ok": True, **result}


# ── balance-prompt ────────────────────────────────────────────────────────────

@router.post("/balance-prompt", dependencies=[Depends(_verify_secret)])
async def cron_balance_prompt(request: Request):
    """
    Every 14 days — ask the whitelisted user for their current bank balance.
    Idempotent: at most one prompt per 24 h.
    """
    pool = request.app.state.pool
    bot = request.app.state.telegram_app.bot

    row = await pool.fetchrow(
        "SELECT id, balance_prompt_sent_at FROM users WHERE telegram_id = $1",
        TELEGRAM_ALLOWED_ID,
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not registered — run /start first")

    last_sent = row["balance_prompt_sent_at"]
    now = datetime.now(timezone.utc)

    if last_sent and (now - last_sent) < timedelta(hours=24):
        return {"ok": True, "skipped": True, "reason": "already sent within 24h"}

    await bot.send_message(
        chat_id=TELEGRAM_ALLOWED_ID,
        text=(
            "💰 Balance check!\n\n"
            "Reply with your current total bank balance (e.g. 48200 or 48k).\n"
            "I'll reconcile it against your logged expenses."
        ),
    )

    await pool.execute(
        "UPDATE users SET balance_prompt_sent_at = $1, awaiting_balance = true WHERE id = $2",
        now,
        str(row["id"]),
    )

    return {"ok": True, "skipped": False}


# ── weekly-summary (stub) ─────────────────────────────────────────────────────

@router.post("/weekly-summary", dependencies=[Depends(_verify_secret)])
async def cron_weekly_summary(request: Request):
    """Sun 19:00 IST — weekly digest (full implementation in Phase 3)."""
    return {"ok": True, "message": "weekly-summary stub — full implementation in Phase 3"}


# ── monthly-summary (stub) ────────────────────────────────────────────────────

@router.post("/monthly-summary", dependencies=[Depends(_verify_secret)])
async def cron_monthly_summary(request: Request):
    """1st 09:00 IST — monthly digest + detection scan (full implementation in Phase 3)."""
    return {"ok": True, "message": "monthly-summary stub — full implementation in Phase 3"}
