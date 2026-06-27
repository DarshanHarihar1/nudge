from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ai.classify import classify_expense
from bot.utils.format import format_amount
from db.queries import (
    confirm_expense,
    create_expense,
    delete_expense,
    get_category_by_name,
    get_expense_by_update_id,
    get_user,
    list_categories,
    recategorize_expense,
)

CB_OK = "exp:ok:"
CB_RECAT = "exp:recat:"
CB_CAT = "exp:cat:"
CB_DEL = "exp:del:"


def _confirm_keyboard(expense_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ OK", callback_data=f"{CB_OK}{expense_id}"),
                InlineKeyboardButton(
                    "✏️ Recategorize", callback_data=f"{CB_RECAT}{expense_id}"
                ),
                InlineKeyboardButton("🗑 Delete", callback_data=f"{CB_DEL}{expense_id}"),
            ]
        ]
    )


async def expense_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text:
        return

    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    # Idempotency: skip if Telegram retries the same webhook update
    existing = await get_expense_by_update_id(pool, update.update_id)
    if existing:
        return

    thinking_msg = await update.message.reply_text("⏳ Logging…")

    try:
        classified = await classify_expense(text)
    except Exception:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=thinking_msg.message_id,
            text="❌ Couldn't classify that. Try again or rephrase.",
        )
        return

    category = await get_category_by_name(pool, str(user["id"]), classified.category)
    if not category:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=thinking_msg.message_id,
            text="❌ Internal error: category not found. Run /start to reset categories.",
        )
        return

    expense = await create_expense(
        pool,
        user_id=str(user["id"]),
        amount=classified.amount,
        currency=classified.currency,
        category_id=str(category["id"]),
        merchant=classified.merchant,
        note=classified.note,
        raw_text=text,
        source="telegram",
        status="pending",
        confidence=classified.confidence,
        llm_provider=classified.provider,
        telegram_update_id=update.update_id,
    )

    label = f"{format_amount(classified.amount, classified.currency)} → {category['emoji']} {category['name']}"
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=thinking_msg.message_id,
        text=f"Logged {label}",
        reply_markup=_confirm_keyboard(str(expense["id"])),
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    pool = context.bot_data["pool"]

    await query.answer()

    if data.startswith(CB_OK):
        expense_id = data[len(CB_OK):]
        await confirm_expense(pool, expense_id)
        await query.edit_message_reply_markup(reply_markup=None)

    elif data.startswith(CB_DEL):
        expense_id = data[len(CB_DEL):]
        await delete_expense(pool, expense_id)
        await query.edit_message_text("Deleted.")

    elif data.startswith(CB_RECAT):
        expense_id = data[len(CB_RECAT):]
        user = await get_user(pool, update.effective_user.id)
        if not user:
            return

        cats = await list_categories(pool, str(user["id"]))
        rows: list[list[InlineKeyboardButton]] = []
        current_row: list[InlineKeyboardButton] = []
        for i, c in enumerate(cats):
            current_row.append(
                InlineKeyboardButton(
                    f"{c['emoji']} {c['name']}",
                    callback_data=f"{CB_CAT}{expense_id}:{c['id']}",
                )
            )
            if len(current_row) == 3:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)

        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith(CB_CAT):
        rest = data[len(CB_CAT):]
        colon_idx = rest.index(":")
        expense_id = rest[:colon_idx]
        category_id = rest[colon_idx + 1:]

        await recategorize_expense(pool, expense_id, category_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.answer("Category updated ✓")
