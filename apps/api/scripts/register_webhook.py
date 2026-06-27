"""Run once after deploy to point Telegram to your webhook URL."""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def register():
    from telegram import Bot

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    secret = os.environ["TELEGRAM_WEBHOOK_SECRET"]
    app_url = os.environ["APP_URL"]

    bot = Bot(token=token)
    webhook_url = f"{app_url.rstrip('/')}/webhook"

    await bot.set_webhook(
        url=webhook_url,
        secret_token=secret,
        allowed_updates=["message", "callback_query"],
    )
    info = await bot.get_webhook_info()
    print(f"Webhook set: {info.url}")
    print(f"Pending updates: {info.pending_update_count}")


if __name__ == "__main__":
    asyncio.run(register())
