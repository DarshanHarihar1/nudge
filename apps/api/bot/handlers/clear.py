"""Handles the [Yes, clear]/[Cancel] callback on the /clear confirmation."""
from telegram import Update
from telegram.ext import ContextTypes

from bot.commands.clear import CB_CLEAR_NO, CB_CLEAR_YES
from db.queries import clear_expenses, get_user


async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    pool = context.bot_data["pool"]
    await query.answer()

    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    if query.data == CB_CLEAR_YES:
        cleared = await clear_expenses(pool, str(user["id"]))
        await query.edit_message_text(
            f"🧹 Cleared {cleared} expense(s). Your dashboard is now empty.\n\n"
            "Changed your mind? Send /restore to bring them all back."
        )
    elif query.data == CB_CLEAR_NO:
        await query.edit_message_text("Cancelled — nothing was cleared.")
