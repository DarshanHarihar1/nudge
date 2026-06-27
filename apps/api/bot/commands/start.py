from telegram import Update
from telegram.ext import ContextTypes

from db.queries import upsert_user, seed_categories


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["pool"]
    tg_user = update.effective_user

    db_user = await upsert_user(pool, tg_user.id, tg_user.first_name)
    await seed_categories(pool, str(db_user["id"]))

    await update.message.reply_text(
        f"👋 Hey {tg_user.first_name}! Nudge is ready.\n\n"
        "Send me any expense like:\n"
        '• "250 lunch"\n'
        '• "cab to airport 480"\n'
        '• "bought shoes 2999"\n\n'
        "I'll classify it and log it automatically.\n\n"
        "Commands: /recent /undo /help"
    )
