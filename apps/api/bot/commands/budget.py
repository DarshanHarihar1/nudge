from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.format import format_amount
from db.queries import get_category_mtd_spend, get_user, list_categories


def _pct_bar(pct: float, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/budget — show all categories with budgets and MTD spend."""
    pool = context.bot_data["pool"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        return

    cats = await list_categories(pool, str(user["id"]))
    budgeted = [c for c in cats if c.get("monthly_budget") is not None]

    if not budgeted:
        await update.message.reply_text(
            "No budgets set yet.\n\nYou can set budgets via the dashboard or the API."
        )
        return

    currency = user.get("base_currency", "INR")
    lines = []
    for c in budgeted:
        budget = Decimal(str(c["monthly_budget"]))
        spent = await get_category_mtd_spend(pool, str(user["id"]), str(c["id"]))
        pct = float(spent / budget * 100) if budget > 0 else 0.0
        bar = _pct_bar(min(pct, 100))
        status = "🚨" if pct >= 100 else ("⚠️" if pct >= 80 else "✅")
        lines.append(
            f"{status} {c['emoji']} {c['name']}\n"
            f"   {bar} {pct:.0f}%\n"
            f"   {format_amount(spent, currency)} / {format_amount(budget, currency)}"
        )

    await update.message.reply_text("*Budget Status — This Month*\n\n" + "\n\n".join(lines), parse_mode="Markdown")
