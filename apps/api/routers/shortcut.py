"""
Shortcut endpoint — lets iPhone Shortcuts log expenses directly.

Auth: Bearer <CRON_SECRET> (same secret used by cron jobs).
Get your token by sending /mytoken to the bot.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db.queries import get_user, list_categories
from routers.auth import require_session

router = APIRouter(prefix="/shortcut", tags=["shortcut"])


class ShortcutExpense(BaseModel):
    amount: float
    category: str   # case-insensitive name, e.g. "Food" or "food"
    note: Optional[str] = None


@router.post("/expense", status_code=201)
async def create_shortcut_expense(
    request: Request,
    body: ShortcutExpense,
    telegram_id: int = Depends(require_session),
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
