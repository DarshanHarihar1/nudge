import asyncpg
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_ALLOWED_ID, TELEGRAM_BOT_TOKEN
from bot.commands.balance import balance_command
from bot.commands.budget import budget_command
from bot.commands.help import help_command
from bot.commands.recent import recent_command
from bot.commands.start import start_command
from bot.commands.undo import undo_command
from bot.handlers.expense import callback_handler
from bot.handlers.text_router import text_router


def create_application(pool: asyncpg.Pool) -> Application:
    allowed = filters.User(user_id=TELEGRAM_ALLOWED_ID)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["pool"] = pool

    app.add_handler(CommandHandler("start", start_command, filters=allowed))
    app.add_handler(CommandHandler("recent", recent_command, filters=allowed))
    app.add_handler(CommandHandler("undo", undo_command, filters=allowed))
    app.add_handler(CommandHandler("balance", balance_command, filters=allowed))
    app.add_handler(CommandHandler("budget", budget_command, filters=allowed))
    app.add_handler(CommandHandler("help", help_command, filters=allowed))

    # Callback queries carry no user filter in PTB — guarded inside handler
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Free-text → routed to balance capture or expense classification
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & allowed, text_router)
    )

    return app
