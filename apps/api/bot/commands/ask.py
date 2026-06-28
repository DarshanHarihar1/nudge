from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.nl_query import process_nl_query


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ask <question> — natural-language query over your spending."""
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            'Ask a question, e.g. "/ask top merchants last week" or "/ask how much on food this month".'
        )
        return
    await process_nl_query(update, context, text)
