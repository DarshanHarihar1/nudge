"""
Routes incoming text messages:
- If the user is in 'awaiting_balance' state and the message is a valid number → balance capture
- Otherwise → expense classification
"""
from telegram import Update
from telegram.ext import ContextTypes

from db.queries import get_user
from services.balance import handle_balance_capture
from utils.balance_parser import parse_balance
from bot.handlers.expense import expense_handler


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text:
        return

    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    if user.get("awaiting_balance"):
        amount = parse_balance(text)
        if amount is not None:
            await handle_balance_capture(
                pool=pool,
                bot=context.bot,
                user=user,
                chat_id=update.effective_chat.id,
                amount=amount,
            )
            return

    await expense_handler(update, context)
