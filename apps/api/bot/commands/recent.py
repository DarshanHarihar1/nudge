from telegram import Update
from telegram.ext import ContextTypes

from db.queries import get_user, list_recent_expenses
from bot.utils.format import format_amount


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    items = await list_recent_expenses(pool, str(user["id"]), 10)
    if not items:
        await update.message.reply_text("No expenses logged yet.")
        return

    lines = []
    for i, e in enumerate(items, 1):
        emoji = e.get("category_emoji") or "📦"
        name = e.get("category_name") or "Misc"
        date = e["spent_at"].strftime("%-d %b")
        merchant = f"  ({e['merchant']})" if e.get("merchant") else ""
        lines.append(
            f"{i}. {emoji} {format_amount(e['amount'], e['currency'])} → {name}  · {date}{merchant}"
        )

    await update.message.reply_text("Recent expenses:\n\n" + "\n".join(lines))
