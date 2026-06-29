import asyncpg
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_ALLOWED_ID, TELEGRAM_BOT_TOKEN
from bot.commands.ask import ask_command
from bot.commands.budget import budget_command
from bot.commands.clear import clear_command, restore_command
from bot.commands.help import help_command
from bot.commands.login import login_command
from bot.commands.recent import recent_command
from bot.commands.start import start_command
from bot.commands.undo import undo_command
from bot.handlers.clear import clear_callback
from bot.handlers.expense import callback_handler
from bot.handlers.suggestion import suggestion_callback
from bot.handlers.text_router import text_router


def create_application(pool: asyncpg.Pool) -> Application:
    allowed = filters.User(user_id=TELEGRAM_ALLOWED_ID)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["pool"] = pool

    app.add_handler(CommandHandler("start", start_command, filters=allowed))
    app.add_handler(CommandHandler("recent", recent_command, filters=allowed))
    app.add_handler(CommandHandler("undo", undo_command, filters=allowed))
    app.add_handler(CommandHandler("budget", budget_command, filters=allowed))
    app.add_handler(CommandHandler("ask", ask_command, filters=allowed))
    app.add_handler(CommandHandler("login", login_command, filters=allowed))
    app.add_handler(CommandHandler("clear", clear_command, filters=allowed))
    app.add_handler(CommandHandler("restore", restore_command, filters=allowed))
    app.add_handler(CommandHandler("help", help_command, filters=allowed))

    # Callback queries — routed by data prefix. Guarded inside each handler.
    app.add_handler(CallbackQueryHandler(callback_handler, pattern=r"^exp:"))
    app.add_handler(CallbackQueryHandler(suggestion_callback, pattern=r"^sug:"))
    app.add_handler(CallbackQueryHandler(clear_callback, pattern=r"^clr:"))

    # Free-text → balance reply / NL query / expense classification
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & allowed, text_router)
    )

    return app
