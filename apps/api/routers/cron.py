"""
Cron endpoints — all require Authorization: Bearer <CRON_SECRET>.
Called by GitHub Actions on schedule.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import CRON_SECRET, TELEGRAM_ALLOWED_ID
from services.detection import run_detection
from services.recurring import apply_recurring_items
from services.summary import send_monthly_summary, send_weekly_summary

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


# ── weekly-summary (stub) ─────────────────────────────────────────────────────

@router.post("/weekly-summary", dependencies=[Depends(_verify_secret)])
async def cron_weekly_summary(request: Request):
    """Sun 19:00 IST — weekly digest."""
    pool = request.app.state.pool
    bot = request.app.state.telegram_app.bot
    result = await send_weekly_summary(pool, bot, TELEGRAM_ALLOWED_ID)
    return {"ok": True, **result}


# ── monthly-summary + recurring detection ─────────────────────────────────────

@router.post("/monthly-summary", dependencies=[Depends(_verify_secret)])
async def cron_monthly_summary(request: Request):
    """1st 09:00 IST — monthly digest + recurring-expense detection scan."""
    pool = request.app.state.pool
    bot = request.app.state.telegram_app.bot
    summary = await send_monthly_summary(pool, bot, TELEGRAM_ALLOWED_ID)
    detection = await run_detection(pool, bot, TELEGRAM_ALLOWED_ID)
    return {"ok": True, "summary": summary, "detection": detection}
