from telegram import Update
from telegram.ext import ContextTypes

from db.queries import get_user, get_last_expense, delete_expense
from bot.utils.format import format_amount


async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    last = await get_last_expense(pool, str(user["id"]))
    if not last:
        await update.message.reply_text("Nothing to undo.")
        return

    await delete_expense(pool, str(last["id"]))

    emoji = last.get("category_emoji") or ""
    name = last.get("category_name") or "Misc"
    await update.message.reply_text(
        f"🗑 Deleted: {format_amount(last['amount'], last['currency'])} → {emoji} {name}"
    )
