import hashlib
import hmac
import time
from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import CRON_SECRET, DASHBOARD_URL

LINK_TTL_SECONDS = 300  # 5 minutes


def _make_token(telegram_id: int, ttl_seconds: int = LINK_TTL_SECONDS) -> str:
    """Sign a short-lived magic-link token the web app can verify.

    Format: "<telegram_id>.<exp>.<hmac_sha256('<telegram_id>.<exp>', CRON_SECRET)>"
    The web /api/login route recomputes the HMAC with the same shared secret.
    """
    exp = int(time.time()) + ttl_seconds
    payload = f"{telegram_id}.{exp}"
    sig = hmac.new(
        CRON_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{sig}"


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    token = _make_token(user.id)
    url = f"{DASHBOARD_URL.rstrip('/')}/api/login?token={quote(token)}"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📊 Open Dashboard", url=url)]]
    )
    await update.message.reply_text(
        "Tap below to open your dashboard.\n"
        "This sign-in link is valid for 5 minutes.",
        reply_markup=keyboard,
    )
