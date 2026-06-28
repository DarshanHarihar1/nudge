"""Dashboard analytics aggregation and NL-query executors."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import asyncpg

from db.queries import (
    get_balance_trend,
    get_count_expenses,
    get_latest_reconciliation,
    get_latest_snapshot,
    get_recurring_credit_total,
    get_sum_by_category,
    get_spend_over_time,
    get_top_merchants,
    get_total_spend,
)
from utils.finance import savings_rate


def _f(v) -> float:
    return float(v) if v is not None else 0.0


async def build_analytics(
    pool: asyncpg.Pool, user_id: str, start: datetime, end: datetime
) -> dict:
    """Assemble the full analytics payload for the dashboard Spending/Overview pages."""
    total = await get_total_spend(pool, user_id, start, end)
    by_cat = await get_sum_by_category(pool, user_id, start, end)
    over_time = await get_spend_over_time(pool, user_id, start, end)
    merchants = await get_top_merchants(pool, user_id, start, end, limit=10)
    income = await get_recurring_credit_total(pool, user_id, start, end)
    trend = await get_balance_trend(pool, user_id)

    rate = savings_rate(income, total)

    return {
        "totalSpend": _f(total),
        "byCategory": [
            {
                "name": r["name"],
                "emoji": r["emoji"],
                "amount": _f(r["amount"]),
                "budget": _f(r["budget"]) if r["budget"] is not None else None,
            }
            for r in by_cat
        ],
        "spendOverTime": [
            {"date": r["date"], "amount": _f(r["amount"])} for r in over_time
        ],
        "topMerchants": [
            {"merchant": r["merchant"], "amount": _f(r["amount"]), "count": int(r["count"])}
            for r in merchants
        ],
        "savingsRate": rate,
        "balanceTrend": [
            {"date": r["date"], "balance": _f(r["balance"])} for r in trend
        ],
    }


# ── NL query executors ────────────────────────────────────────────────────────

async def execute_nl_query(
    pool: asyncpg.Pool, user_id: str, function: str, params: dict, start: datetime, end: datetime
) -> list[dict]:
    """Run the predefined query for a validated {function, params} mapping."""
    if function == "totalSpend":
        total = await get_total_spend(pool, user_id, start, end)
        return [{"total": _f(total)}]

    if function == "countExpenses":
        count = await get_count_expenses(pool, user_id, start, end)
        return [{"count": count}]

    if function == "sumByCategory":
        rows = await get_sum_by_category(
            pool, user_id, start, end, category=params.get("category")
        )
        return [
            {"name": r["name"], "emoji": r["emoji"], "amount": _f(r["amount"])}
            for r in rows
        ]

    if function == "topMerchants":
        rows = await get_top_merchants(
            pool, user_id, start, end, limit=params.get("limit", 5)
        )
        return [
            {"merchant": r["merchant"], "amount": _f(r["amount"]), "count": int(r["count"])}
            for r in rows
        ]

    return []
