"""
Shortcut endpoint — lets iPhone Shortcuts log expenses directly.

Auth: stateless HMAC token derived from SESSION_SECRET.
Get your token by sending /mytoken to the bot.
"""
from __future__ import annotations

import hashlib
import hmac
import base64
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from config import SESSION_SECRET, TELEGRAM_ALLOWED_ID
from db.queries import get_user, list_categories

router = APIRouter(prefix="/shortcut", tags=["shortcut"])


def derive_shortcut_token(telegram_id: int) -> str:
    """Deterministic per-user token: HMAC-SHA256(SESSION_SECRET, 'shortcut:{telegram_id}')."""
    key = SESSION_SECRET.encode()
    msg = f"shortcut:{telegram_id}".encode()
    raw = hmac.digest(key, msg, "sha256")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _require_token(request: Request) -> int:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth[7:]
    expected = derive_shortcut_token(TELEGRAM_ALLOWED_ID)
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid token")
    return TELEGRAM_ALLOWED_ID


class ShortcutExpense(BaseModel):
    amount: float
    category: str   # case-insensitive name, e.g. "Food" or "food"
    note: Optional[str] = None


@router.post("/expense", status_code=201)
async def create_shortcut_expense(
    request: Request,
    body: ShortcutExpense,
    telegram_id: int = Depends(_require_token),
):
    pool = request.app.state.pool
    user = await get_user(pool, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not registered")

    cats = await list_categories(pool, str(user["id"]))
    cat = next((c for c in cats if c["name"].lower() == body.category.lower()), None)
    if not cat:
        available = ", ".join(c["name"] for c in cats)
        raise HTTPException(status_code=422, detail=f"Unknown category. Available: {available}")

    row = await pool.fetchrow(
        """
        INSERT INTO expenses (
            user_id, amount, currency, category_id, note,
            raw_text, source, status, confidence
        )
        VALUES ($1, $2, 'INR', $3, $4, $5, 'telegram', 'confirmed', 1.0)
        RETURNING id
        """,
        str(user["id"]),
        str(body.amount),
        str(cat["id"]),
        body.note,
        f"shortcut: {body.amount} {body.category}",
    )
    return {"ok": True, "id": str(row["id"])}
