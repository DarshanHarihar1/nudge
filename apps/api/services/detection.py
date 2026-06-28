"""Recurring-expense detection — orchestrates DB + pure algorithm + bot suggestions."""
from __future__ import annotations

import asyncpg
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from bot.utils.format import format_amount
from db.queries import (
    get_existing_recurring_merchants,
    get_expenses_for_detection,
    get_suppressed_merchants,
    get_user,
    upsert_suggestion,
)
from utils.detection import detect_recurring_candidates
from utils.ranges import resolve_range

CB_SUG_YES = "sug:y:"
CB_SUG_NO = "sug:n:"


async def run_detection(pool: asyncpg.Pool, bot: Bot, telegram_id: int) -> dict:
    user = await get_user(pool, telegram_id)
    if not user:
        return {"suggested": 0, "reason": "user not registered"}
    user_id = str(user["id"])

    # Look back over the last 3 months
    since, _ = resolve_range("last_3_months")
    expenses = await get_expenses_for_detection(pool, user_id, since)
    existing = await get_existing_recurring_merchants(pool, user_id)
    suppressed = await get_suppressed_merchants(pool, user_id)

    candidates = detect_recurring_candidates(expenses, existing, suppressed)

    suggested = 0
    for c in candidates:
        suggestion = await upsert_suggestion(pool, user_id, c["merchant"], float(c["amount"]))
        if suggestion["status"] != "pending":
            continue
        kb = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Yes", callback_data=f"{CB_SUG_YES}{suggestion['id']}"),
                InlineKeyboardButton("🚫 No", callback_data=f"{CB_SUG_NO}{suggestion['id']}"),
            ]]
        )
        await bot.send_message(
            chat_id=telegram_id,
            text=(
                f"🔁 Looks like *{c['merchant']}* {format_amount(c['amount'])} "
                f"recurs (~{c['months']} months). Add it as a recurring item?"
            ),
            parse_mode="Markdown",
            reply_markup=kb,
        )
        suggested += 1

    return {"suggested": suggested, "candidates": len(candidates)}
