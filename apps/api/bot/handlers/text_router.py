"""
Routes incoming text messages:
- If the message is a natural-language query (ends with "?") → query executor
- Otherwise → expense classification
"""
from telegram import Update
from telegram.ext import ContextTypes

from db.queries import get_user
from bot.handlers.expense import expense_handler
from bot.handlers.nl_query import is_query, process_nl_query


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text:
        return

    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    # 1. Natural-language query — message ending with "?"
    if is_query(text):
        await process_nl_query(update, context, text)
        return

    # 2. Otherwise treat as an expense to log
    await expense_handler(update, context)
