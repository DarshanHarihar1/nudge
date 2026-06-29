from telegram import Update
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Nudge — Personal Finance Tracker\n\n"
        "*Logging expenses*\n"
        "Just type any expense in plain English:\n"
        '• "250 lunch with team"\n'
        '• "Swiggy 480"\n'
        '• "bought shoes 2999"\n\n'
        "*Ask questions* (end with ?)\n"
        '• "how much on food this month?"\n'
        "• /ask top merchants last week\n\n"
        "*Commands*\n"
        "/recent — Last 10 expenses\n"
        "/budget — Budget status this month\n"
        "/ask <question> — Query your spending\n"
        "/login — Open the web dashboard\n"
        "/undo — Delete the last expense\n"
        "/clear — Hide all expenses from the dashboard\n"
        "/restore — Undo the last /clear\n"
        "/help — Show this message",
        parse_mode="Markdown",
    )
