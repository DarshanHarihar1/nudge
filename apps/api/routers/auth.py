"""
Dashboard authentication via Telegram Login Widget.

Flow:
  1. Frontend renders the Telegram Login Widget pointed at /auth/telegram/callback.
  2. Telegram redirects here with signed user data (query params).
  3. We verify the HMAC signature, confirm it's the whitelisted user, set a
     signed session cookie, and redirect to the dashboard.

The session dependency (`require_session`) is reused by the dashboard router.
A Bearer <CRON_SECRET> header is also accepted for server-side/testing access.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from config import (
    APP_URL,
    CRON_SECRET,
    SESSION_SECRET,
    TELEGRAM_ALLOWED_ID,
    TELEGRAM_BOT_TOKEN,
)
from utils.session import sign_session, verify_session
from utils.telegram_auth import verify_telegram_login

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "nudge_session"
COOKIE_MAX_AGE = 86_400  # 24h


@router.get("/telegram/callback")
async def telegram_callback(request: Request):
    data = dict(request.query_params)

    if not verify_telegram_login(data, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid Telegram login signature")

    telegram_id = int(data.get("id", 0))
    if telegram_id != TELEGRAM_ALLOWED_ID:
        raise HTTPException(status_code=403, detail="Not authorized")

    token = sign_session(telegram_id, SESSION_SECRET, ttl_seconds=COOKIE_MAX_AGE)
    redirect = RedirectResponse(url=f"{APP_URL.rstrip('/')}/dashboard", status_code=303)
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return redirect


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


def require_session(request: Request) -> int:
    """
    FastAPI dependency: returns the authenticated telegram_id.
    Accepts either a valid session cookie or a Bearer <CRON_SECRET> header.
    Raises 401 otherwise.
    """
    # Bearer CRON_SECRET escape hatch for server-side / testing
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == CRON_SECRET:
        return TELEGRAM_ALLOWED_ID

    token = request.cookies.get(COOKIE_NAME)
    if token:
        tid = verify_session(token, SESSION_SECRET)
        if tid == TELEGRAM_ALLOWED_ID:
            return tid

    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/session")
async def session_info(telegram_id: int = Depends(require_session)):
    return {"authenticated": True, "telegram_id": telegram_id}
