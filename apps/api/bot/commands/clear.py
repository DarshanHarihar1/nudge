from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db.queries import (
    count_active_expenses,
    count_cleared_expenses,
    get_user,
    restore_expenses,
)

# Callback data prefixes for the confirmation keyboard
CB_CLEAR_YES = "clr:yes"
CB_CLEAR_NO = "clr:no"


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/clear — remove all expenses from the dashboard (reversible via /restore)."""
    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    count = await count_active_expenses(pool, str(user["id"]))
    if count == 0:
        await update.message.reply_text("Nothing to clear — you have no expenses logged.")
        return

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(f"🧹 Yes, clear {count}", callback_data=CB_CLEAR_YES),
            InlineKeyboardButton("Cancel", callback_data=CB_CLEAR_NO),
        ]]
    )
    await update.message.reply_text(
        f"⚠️ This will hide all *{count}* expense(s) from your dashboard.\n\n"
        "You can undo it with /restore afterwards. Proceed?",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/restore — undo the last /clear."""
    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    pending = await count_cleared_expenses(pool, str(user["id"]))
    if pending == 0:
        await update.message.reply_text("Nothing to restore.")
        return

    restored = await restore_expenses(pool, str(user["id"]))
    await update.message.reply_text(
        f"♻️ Restored {restored} expense(s). They're back on your dashboard."
    )
