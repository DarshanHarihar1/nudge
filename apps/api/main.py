from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from telegram import Update
from telegram.ext import Application

from config import TELEGRAM_WEBHOOK_SECRET
from db.client import close_pool, create_pool
from bot.application import create_application
from routers.cron import router as cron_router
from routers.dashboard import router as dashboard_router

_telegram_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool()
    telegram_app = create_application(pool)
    await telegram_app.initialize()

    # Expose on app.state so routers can access them via request.app.state
    app.state.pool = pool
    app.state.telegram_app = telegram_app

    global _telegram_app
    _telegram_app = telegram_app

    yield

    await telegram_app.shutdown()
    await close_pool()


app = FastAPI(title="Nudge API", lifespan=lifespan)

app.include_router(cron_router)
app.include_router(dashboard_router)


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
    pool = getattr(app.state, "pool", None)
    if pool:
        # Ping DB so Supabase doesn't pause due to inactivity
        await pool.fetchval("SELECT 1")
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}
