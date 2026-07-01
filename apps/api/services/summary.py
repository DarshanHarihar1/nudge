"""Weekly and monthly summary generation + sending."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import asyncpg
from telegram import Bot

from config import SUMMARY_INSIGHT_ENABLED
from db.queries import (
    get_sum_by_category,
    get_total_spend,
    get_user,
)
from utils.ranges import resolve_range
from utils.summary_templates import (
    build_daily_summary,
    build_expense_reminder,
    build_monthly_summary,
    build_weekly_summary,
)
from utils.timezone import now_ist


async def _over_budget(pool, user_id, start, end) -> list[dict]:
    """Categories where MTD spend is ≥80% of their budget."""
    rows = await get_sum_by_category(pool, user_id, start, end)
    out = []
    for r in rows:
        budget = r.get("budget")
        if budget is None:
            continue
        budget_dec = Decimal(str(budget))
        if budget_dec <= 0:
            continue
        pct = float(Decimal(str(r["amount"])) / budget_dec * 100)
        if pct >= 80:
            out.append({"name": r["name"], "emoji": r["emoji"], "pct": pct})
    return out


async def _maybe_insight(spend: Decimal, top: list[dict]) -> str | None:
    if not SUMMARY_INSIGHT_ENABLED:
        return None
    import os

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=api_key)
        top_str = ", ".join(f"{c['name']} ₹{int(float(c['amount']))}" for c in top[:3])
        resp = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Give ONE short, friendly one-line insight about the user's spending. No preamble."},
                {"role": "user", "content": f"Total ₹{int(float(spend))}. Top: {top_str}."},
            ],
            temperature=0.7,
            max_tokens=60,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


async def send_daily_summary(pool: asyncpg.Pool, bot: Bot, telegram_id: int) -> dict:
    user = await get_user(pool, telegram_id)
    if not user:
        return {"sent": False, "reason": "user not registered"}
    user_id = str(user["id"])
    currency = user.get("base_currency", "INR")

    start, end = resolve_range("today")
    total = await get_total_spend(pool, user_id, start, end)
    by_cat = await get_sum_by_category(pool, user_id, start, end)
    expense_count = await pool.fetchval(
        """
        SELECT COUNT(*) FROM expenses
        WHERE user_id = $1
          AND spent_at >= $2 AND spent_at < $3
          AND status = 'confirmed'
        """,
        user_id, start, end,
    )

    date_label = now_ist().strftime("%-d %b")
    text = build_daily_summary(
        date_label=date_label,
        total_spend=total,
        top_categories=[{"name": c["name"], "emoji": c["emoji"], "amount": c["amount"]} for c in by_cat],
        expense_count=int(expense_count or 0),
        currency=currency,
    )
    await bot.send_message(chat_id=telegram_id, text=text, parse_mode="Markdown")
    return {"sent": True}


async def send_expense_reminder(pool: asyncpg.Pool, bot: Bot, telegram_id: int) -> dict:
    user = await get_user(pool, telegram_id)
    if not user:
        return {"sent": False, "reason": "user not registered"}

    # Derive slot from current IST hour: 9am→0, 1pm→1, 7pm→2
    hour = now_ist().hour
    slot = 0 if hour < 12 else (1 if hour < 16 else 2)
    text = build_expense_reminder(slot)
    await bot.send_message(chat_id=telegram_id, text=text)
    return {"sent": True, "slot": slot}


async def send_weekly_summary(pool: asyncpg.Pool, bot: Bot, telegram_id: int) -> dict:
    user = await get_user(pool, telegram_id)
    if not user:
        return {"sent": False, "reason": "user not registered"}
    user_id = str(user["id"])
    currency = user.get("base_currency", "INR")

    start, end = resolve_range("week")
    total = await get_total_spend(pool, user_id, start, end)
    top = await get_sum_by_category(pool, user_id, start, end)
    over = await _over_budget(pool, user_id, start, end)
    insight = await _maybe_insight(total, top)

    text = build_weekly_summary(
        total_spend=total,
        top_categories=[{"name": c["name"], "emoji": c["emoji"], "amount": c["amount"]} for c in top],
        over_budget=over,
        insight=insight,
        currency=currency,
    )
    await bot.send_message(chat_id=telegram_id, text=text, parse_mode="Markdown")
    return {"sent": True}


async def send_monthly_summary(pool: asyncpg.Pool, bot: Bot, telegram_id: int) -> dict:
    user = await get_user(pool, telegram_id)
    if not user:
        return {"sent": False, "reason": "user not registered"}
    user_id = str(user["id"])
    currency = user.get("base_currency", "INR")

    start, end = resolve_range("month")
    total = await get_total_spend(pool, user_id, start, end)
    top = await get_sum_by_category(pool, user_id, start, end)
    over = await _over_budget(pool, user_id, start, end)
    insight = await _maybe_insight(total, top)

    text = build_monthly_summary(
        total_spend=total,
        top_categories=[{"name": c["name"], "emoji": c["emoji"], "amount": c["amount"]} for c in top],
        over_budget=over,
        insight=insight,
        currency=currency,
    )
    await bot.send_message(chat_id=telegram_id, text=text, parse_mode="Markdown")
    return {"sent": True}
