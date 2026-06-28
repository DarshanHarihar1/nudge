"""Natural-language query handling for the bot."""
from telegram import Update
from telegram.ext import ContextTypes

from ai.nl_query import map_nl_query
from db.queries import get_user
from services.analytics import execute_nl_query
from utils.ranges import resolve_range
from utils.summary_templates import format_nl_answer

FALLBACK = (
    "I didn't understand that query. Try:\n"
    '• "how much on food this month?"\n'
    '• "/ask top merchants last week"'
)


async def process_nl_query(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    text = text.strip()
    if not text:
        await update.message.reply_text(FALLBACK)
        return

    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    mapping = await map_nl_query(text)
    if not mapping:
        await update.message.reply_text(FALLBACK)
        return

    start, end = resolve_range(mapping["params"]["range"])
    rows = await execute_nl_query(
        pool, str(user["id"]), mapping["function"], mapping["params"], start, end
    )
    currency = user.get("base_currency", "INR")
    answer = format_nl_answer(mapping["function"], mapping["params"], rows, currency)
    await update.message.reply_text(answer)


def is_query(text: str) -> bool:
    """A free-text message is treated as a query if it ends with a question mark."""
    return text.strip().endswith("?")
