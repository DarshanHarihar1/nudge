"""
Tonight's questions, in one go: every bank payment still waiting for a
category from the last 24h, each with its own category picker.
"""
from datetime import timedelta

from bot.handlers.expense import recategorize_keyboard
from bot.utils.format import format_amount
from db.queries import get_user, list_unsure_email_expenses
from utils.timezone import IST, now_ist


def format_digest_line(expense: dict, currency: str) -> str:
    when = expense["spent_at"].astimezone(IST).strftime("%H:%M")
    line = f"{format_amount(expense['amount'], currency)} to {expense['merchant'] or 'unknown payee'} at {when}"
    return f"{line}\n{expense['note']}" if expense.get("note") else line


async def send_category_digest(pool, bot, telegram_id: int) -> dict:
    user = await get_user(pool, telegram_id)
    if not user:
        return {"asked": 0}
    user_id = str(user["id"])
    currency = user.get("base_currency", "INR")
    pending = await list_unsure_email_expenses(pool, user_id, now_ist() - timedelta(hours=24))
    if not pending:
        return {"asked": 0}
    await bot.send_message(
        chat_id=telegram_id,
        text=f"🗂 {len(pending)} bank payment{'s' if len(pending) > 1 else ''} need a category:",
    )
    for e in pending:
        await bot.send_message(
            chat_id=telegram_id,
            text=format_digest_line(e, currency),
            reply_markup=await recategorize_keyboard(pool, user_id, str(e["id"])),
        )
    return {"asked": len(pending)}
