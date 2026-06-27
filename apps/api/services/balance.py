"""Balance capture and reconciliation logic."""
from datetime import datetime, timezone
from decimal import Decimal

import asyncpg
from telegram import Bot

from bot.utils.format import format_amount
from db.queries import (
    create_balance_snapshot,
    create_reconciliation,
    get_expenses_sum_in_period,
    get_latest_snapshot,
    set_awaiting_balance,
)
from utils.reconciliation import compute_reconciliation


async def handle_balance_capture(
    pool: asyncpg.Pool,
    bot: Bot,
    user: dict,
    chat_id: int,
    amount: float,
) -> None:
    """
    Called when a user submits a balance (via /balance command or awaiting-balance reply).
    1. Fetches the previous snapshot (if any) for reconciliation.
    2. Writes the new balance_snapshot.
    3. Runs reconciliation math and writes a reconciliations row.
    4. Clears the awaiting_balance flag.
    5. Sends a reply summarising the reconciliation.
    """
    now = datetime.now(timezone.utc)
    user_id = str(user["id"])
    currency = user.get("base_currency", "INR")

    # Fetch prior snapshot before writing the new one
    prior = await get_latest_snapshot(pool, user_id)

    # Write current snapshot
    await create_balance_snapshot(pool, user_id, amount)

    # Clear awaiting flag
    await set_awaiting_balance(pool, user_id, False)

    if prior is None:
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Balance recorded: {format_amount(amount, currency)}\n\n"
            "No previous snapshot — reconciliation starts from next check.",
        )
        return

    opening = Decimal(str(prior["balance"]))
    closing = Decimal(str(amount))
    period_start: datetime = prior["recorded_at"]
    period_end = now

    # Expenses logged manually in the period
    logged_total = await get_expenses_sum_in_period(
        pool, user_id, period_start, period_end, source=None
    )
    # Recurring debits applied in the period
    recurring_debit = await get_expenses_sum_in_period(
        pool, user_id, period_start, period_end, source="recurring_debit"
    )
    # Recurring credits (income) in the period
    recurring_credit = await get_expenses_sum_in_period(
        pool, user_id, period_start, period_end, source="recurring_credit"
    )

    expected_close, discrepancy = compute_reconciliation(
        opening, closing, logged_total, recurring_debit, recurring_credit
    )

    await create_reconciliation(
        pool,
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        opening_balance=opening,
        closing_balance=closing,
        logged_total=logged_total,
        recurring_total=recurring_debit,
        expected_close=expected_close,
        discrepancy=discrepancy,
    )

    threshold = Decimal("100")
    if abs(discrepancy) < threshold:
        summary = f"✅ Accounts balance within {format_amount(threshold, currency)}."
    elif discrepancy > 0:
        summary = (
            f"📊 Expected {format_amount(expected_close, currency)} · "
            f"Actual {format_amount(closing, currency)} · "
            f"Gap {format_amount(abs(discrepancy), currency)} unaccounted."
        )
    else:
        summary = (
            f"📊 Expected {format_amount(expected_close, currency)} · "
            f"Actual {format_amount(closing, currency)} · "
            f"Surplus {format_amount(abs(discrepancy), currency)} over expected."
        )

    days = (period_end - period_start).days
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"💰 Balance recorded: {format_amount(amount, currency)}\n\n"
            f"*Reconciliation ({days}d period)*\n"
            f"Opening: {format_amount(opening, currency)}\n"
            f"Logged expenses: −{format_amount(logged_total, currency)}\n"
            f"Recurring debits: −{format_amount(recurring_debit, currency)}\n"
            f"Recurring credits: +{format_amount(recurring_credit, currency)}\n\n"
            f"{summary}"
        ),
        parse_mode="Markdown",
    )
