"""
Orchestrates the email debit-alert flow: parse -> filter -> dedupe ->
classify -> store -> notify. Mirrors bot/handlers/expense.py's Telegram
text flow, reusing its classification call and confirm/recategorize UI.
"""
from telegram import Bot

from ai.classify import classify_expense
from bot.handlers.expense import post_keyboard, recategorize_keyboard
from bot.utils.format import format_amount
from db.queries import (
    create_expense,
    get_category_by_name,
    get_expense_by_email_ref,
    get_user,
)
from utils.email_parser import parse_ubi_debit_email

# Below this classification confidence, don't guess — ask via the
# recategorize picker immediately instead of showing OK/Recategorize/Delete.
LOW_CONFIDENCE_THRESHOLD = 0.6


def needs_recategorize(confidence: float) -> bool:
    return confidence < LOW_CONFIDENCE_THRESHOLD


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

    if parsed.status.lower() != "success":
        return {"ok": False, "reason": f"status={parsed.status}"}

    if await get_expense_by_email_ref(pool, parsed.rrn):
        return {"ok": False, "reason": "duplicate"}

    user = await get_user(pool, allowed_telegram_id)
    if not user:
        return {"ok": False, "reason": "user_not_registered"}

    try:
        classified = await classify_expense(f"{parsed.amount} at {parsed.payee}")
    except Exception:
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text="⚠️ Got a debit alert I couldn't classify (LLM providers down?). Log it manually if it was real.",
        )
        return {"ok": False, "reason": "classification_failed"}

    category = await get_category_by_name(pool, str(user["id"]), classified.category)
    if not category:
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text="⚠️ Got a debit alert but couldn't match a category. Run /start to reset categories.",
        )
        return {"ok": False, "reason": "category_not_found"}

    low_confidence = needs_recategorize(classified.confidence)

    # Confident guesses are inserted already-confirmed (no tap required to
    # count toward totals/budgets); unsure ones stay pending until a
    # category is picked, same as recategorize_expense() already does.
    expense = await create_expense(
        pool,
        user_id=str(user["id"]),
        amount=parsed.amount,
        currency=parsed.currency,
        category_id=str(category["id"]),
        merchant=parsed.payee,
        raw_text=message_text,
        source="email",
        status="pending" if low_confidence else "confirmed",
        confidence=classified.confidence,
        llm_provider=classified.provider,
        email_ref=parsed.rrn,
    )

    label = (
        f"{format_amount(parsed.amount, parsed.currency)} → "
        f"{category['emoji']} {category['name']} ({parsed.payee})"
    )

    if low_confidence:
        keyboard = await recategorize_keyboard(pool, str(user["id"]), str(expense["id"]))
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f"🏦 {label} — not sure about the category, pick one:",
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f"🏦 Logged {label}",
            reply_markup=post_keyboard(str(expense["id"])),
        )

    return {"ok": True, "id": str(expense["id"])}
