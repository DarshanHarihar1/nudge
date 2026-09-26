"""
Orchestrates the email debit-alert flow: parse -> filter -> dedupe ->
classify -> store -> notify. Mirrors bot/handlers/expense.py's Telegram
text flow, reusing its classification call, budget-alert check, and
confirm/recategorize UI.
"""
from datetime import datetime
from typing import Optional

import asyncpg
from telegram import Bot

from ai.classify import classify_expense
from bot.handlers.expense import check_budget_alert, post_keyboard, recategorize_keyboard
from bot.utils.format import format_amount
from db.queries import (
    create_expense,
    get_category_by_name,
    get_expense_by_email_ref,
    get_user,
    learned_category,
    recent_payee_choices,
)
from utils.email_parser import parse_ubi_debit_email
from utils.timezone import IST

# Confident enough to log without asking.
AUTO_CONFIRM_CONFIDENCE = 0.8
# Unsure and at least this big: ask immediately instead of in tonight's digest.
ASK_NOW_AMOUNT = 5000

# Bank-confirmed non-completions — safe to skip without notifying, since no
# money moved. Any OTHER status is unexpected and gets a Telegram notice
# instead of a silent drop, since the bank template's exact status wording
# beyond "Success" isn't something this parser was built against real
# examples of.
KNOWN_NON_SUCCESS_STATUSES = {"failed", "declined", "rejected"}


def decide_route(confidence: float, amount: float, from_memory: bool) -> str:
    """auto = log confirmed; ask_now = pending + picker now; ask_later = pending, nightly digest."""
    if from_memory or confidence >= AUTO_CONFIRM_CONFIDENCE:
        return "auto"
    return "ask_now" if amount >= ASK_NOW_AMOUNT else "ask_later"


def _parse_spent_at(occurred_at: str) -> Optional[datetime]:
    """Bank format: 'DD-MM-YYYY HH:MM:SS' in IST. Returns None if unparseable."""
    try:
        return datetime.strptime(occurred_at, "%d-%m-%Y %H:%M:%S").replace(tzinfo=IST)
    except (ValueError, TypeError):
        return None


async def process_debit_email(
    pool,
    bot: Bot,
    allowed_telegram_id: int,
    message_text: str,
    subject: str,
) -> dict:
    parsed = parse_ubi_debit_email(message_text)
    if not parsed:
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f'📧 Got a mail from the bank I couldn\'t parse: "{subject}". Log it manually if it was a transaction.',
        )
        return {"ok": False, "reason": "unparseable"}

    status_lower = parsed.status.lower()
    if status_lower != "success":
        if status_lower not in KNOWN_NON_SUCCESS_STATUSES:
            await bot.send_message(
                chat_id=allowed_telegram_id,
                text=f'📧 Got a debit alert with an unexpected status ("{parsed.status}") — log it manually if it was a real transaction.',
            )
        return {"ok": False, "reason": f"status={parsed.status}"}

    if await get_expense_by_email_ref(pool, parsed.rrn):
        return {"ok": False, "reason": "duplicate"}

    user = await get_user(pool, allowed_telegram_id)
    if not user:
        return {"ok": False, "reason": "user_not_registered"}

    user_id = str(user["id"])
    category = await learned_category(pool, user_id, parsed.payee)
    if category:
        confidence, provider = 1.0, "memory"
    else:
        try:
            examples = await recent_payee_choices(pool, user_id)
            classified = await classify_expense(f"{parsed.amount} at {parsed.payee}", examples)
        except Exception:
            await bot.send_message(
                chat_id=allowed_telegram_id,
                text="⚠️ Got a debit alert I couldn't classify (LLM providers down?). Log it manually if it was real.",
            )
            return {"ok": False, "reason": "classification_failed"}
        category = await get_category_by_name(pool, user_id, classified.category)
        if not category:
            await bot.send_message(
                chat_id=allowed_telegram_id,
                text="⚠️ Got a debit alert but couldn't match a category. Run /start to reset categories.",
            )
            return {"ok": False, "reason": "category_not_found"}
        confidence, provider = classified.confidence, classified.provider

    route = decide_route(confidence, parsed.amount, provider == "memory")

    try:
        expense = await create_expense(
            pool,
            user_id=user_id,
            amount=parsed.amount,
            currency=parsed.currency,
            category_id=str(category["id"]),
            merchant=parsed.payee,
            raw_text=message_text,
            source="email",
            status="confirmed" if route == "auto" else "pending",
            confidence=confidence,
            llm_provider=provider,
            email_ref=parsed.rrn,
            spent_at=_parse_spent_at(parsed.occurred_at),
        )
    except asyncpg.UniqueViolationError:
        # Benign race: a concurrent redelivery of the same email won the
        # insert between our pre-check above and this insert. The
        # transaction is already logged under the other request — nothing
        # to notify, this is the same outcome as the pre-check catching it.
        return {"ok": False, "reason": "duplicate"}
    except Exception:
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text="⚠️ Got a debit alert but couldn't save it. Log it manually.",
        )
        return {"ok": False, "reason": "insert_failed"}

    label = (
        f"{format_amount(parsed.amount, parsed.currency)} → "
        f"{category['emoji']} {category['name']} ({parsed.payee})"
    )

    if route == "auto":
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f"🏦 Logged {label}",
            reply_markup=post_keyboard(str(expense["id"])),
        )
        await check_budget_alert(
            pool=pool,
            bot=bot,
            chat_id=allowed_telegram_id,
            user=user,
            category=category,
            currency=parsed.currency,
        )
    elif route == "ask_now":
        keyboard = await recategorize_keyboard(pool, user_id, str(expense["id"]))
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f"🏦 {label} — not sure about the category, pick one:",
            reply_markup=keyboard,
        )
    # ask_later: saved as pending; tonight's digest asks.

    return {"ok": True, "id": str(expense["id"]), "route": route}
