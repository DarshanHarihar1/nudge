"""Apply-recurring cron logic."""
import asyncpg
from telegram import Bot

from bot.utils.format import format_amount
from db.queries import create_expense, get_recurring_items_due_today, mark_recurring_applied
from utils.timezone import today_ist


async def apply_recurring_items(pool: asyncpg.Pool, bot: Bot, allowed_telegram_id: int) -> dict:
    """
    Find all recurring items due today (IST), create expense rows, update last_applied_on.
    Returns a summary dict with counts.
    """
    today = today_ist()
    items = await get_recurring_items_due_today(pool, today)

    applied = []
    for item in items:
        source = "recurring_credit" if item["direction"] == "credit" else "recurring_debit"
        await create_expense(
            pool,
            user_id=str(item["user_id"]),
            amount=float(item["amount"]),
            currency="INR",
            category_id=str(item["category_id"]),
            note=item["name"],
            raw_text=f"[recurring] {item['name']}",
            source=source,
            status="confirmed",
        )
        await mark_recurring_applied(pool, str(item["id"]), today)

        emoji = item.get("category_emoji") or ""
        sign = "+" if item["direction"] == "credit" else ""
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f"{emoji} Recurring applied: {item['name']} {sign}{format_amount(item['amount'])}",
        )
        applied.append(item["name"])

    return {"applied": applied, "count": len(applied)}
