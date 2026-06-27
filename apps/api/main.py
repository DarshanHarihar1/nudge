from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from telegram import Update
from telegram.ext import Application

from config import TELEGRAM_WEBHOOK_SECRET
from db.client import close_pool, create_pool
from bot.application import create_application

_telegram_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram_app
    pool = await create_pool()
    _telegram_app = create_application(pool)
    await _telegram_app.initialize()
    yield
    await _telegram_app.shutdown()
    await close_pool()


app = FastAPI(title="Nudge API", lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    secret = request.headers.get("x-telegram-bot-api-secret-token")
    if not TELEGRAM_WEBHOOK_SECRET or secret != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.json()
    update = Update.de_json(data, _telegram_app.bot)
    await _telegram_app.process_update(update)
    return {"ok": True}


@app.get("/health")
async def health():
    pool = _telegram_app.bot_data.get("pool") if _telegram_app else None
    if pool:
        # Ping DB so Supabase doesn't pause due to inactivity
        await pool.fetchval("SELECT 1")
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}
