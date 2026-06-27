from telegram import Update
from telegram.ext import ContextTypes

from db.queries import get_user
from services.balance import handle_balance_capture
from utils.balance_parser import parse_balance


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/balance <amount> — record current bank balance."""
    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    args = context.args
    raw = " ".join(args) if args else ""
    amount = parse_balance(raw) if raw else None

    if amount is None:
        await update.message.reply_text(
            "Usage: /balance <amount>\nExamples: /balance 48200  /balance 48k  /balance 48,200"
        )
        return

    await handle_balance_capture(
        pool=pool,
        bot=context.bot,
        user=user,
        chat_id=update.effective_chat.id,
        amount=amount,
    )
