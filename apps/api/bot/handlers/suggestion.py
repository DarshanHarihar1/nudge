"""Handles [Yes]/[No] callbacks on recurring-expense detection suggestions."""
from telegram import Update
from telegram.ext import ContextTypes

from config import APP_URL
from db.queries import set_suggestion_status
from services.detection import CB_SUG_NO, CB_SUG_YES


async def suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    pool = context.bot_data["pool"]
    await query.answer()

    if data.startswith(CB_SUG_YES):
        suggestion_id = data[len(CB_SUG_YES):]
        await set_suggestion_status(pool, suggestion_id, "accepted")
        link = f"{APP_URL.rstrip('/')}/dashboard/recurring"
        await query.edit_message_text(
            f"👍 Add it on your dashboard: {link}",
            disable_web_page_preview=True,
        )

    elif data.startswith(CB_SUG_NO):
        suggestion_id = data[len(CB_SUG_NO):]
        await set_suggestion_status(pool, suggestion_id, "suppressed")
        await query.edit_message_text("Got it — I won't suggest that again.")
