import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import APP_URL, CRON_SECRET

logger = logging.getLogger(__name__)


async def mytoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/mytoken — get your iPhone Shortcut auth token and endpoint."""
    try:
        endpoint = f"{APP_URL.rstrip('/')}/shortcut/expense"
        await update.message.reply_text(
            "Your Shortcut Token\n\n"
            f"{CRON_SECRET}\n\n"
            f"Endpoint:\n{endpoint}\n\n"
            "In your Shortcut's Authorization header use:\n"
            f"Bearer {CRON_SECRET}",
        )
    except Exception as e:
        logger.exception("mytoken_command failed")
        await update.message.reply_text(f"Error: {e}")
