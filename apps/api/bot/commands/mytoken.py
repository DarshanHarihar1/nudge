import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import APP_URL
from routers.shortcut import derive_shortcut_token

logger = logging.getLogger(__name__)


async def mytoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/mytoken — get your iPhone Shortcut authentication token."""
    try:
        tg_id = update.effective_user.id
        token = derive_shortcut_token(tg_id)
        endpoint = f"{APP_URL.rstrip('/')}/shortcut/expense"

        await update.message.reply_text(
            "Your Shortcut Token\n\n"
            f"{token}\n\n"
            f"Endpoint:\n{endpoint}\n\n"
            "Paste both into your iPhone Shortcut. Keep the token private.",
        )
    except Exception as e:
        logger.exception("mytoken_command failed")
        await update.message.reply_text(f"Error generating token: {e}")
