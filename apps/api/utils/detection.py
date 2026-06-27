"""
Recurring-expense detection (pure algorithm).

A merchant is flagged as a recurring candidate when its expenses:
  - appear in at least `min_months` distinct calendar months within the lookback window,
  - have amounts that cluster within ±`tolerance` of their mean,
  - are not already configured in recurring_items,
  - have not been suppressed by the user.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from statistics import mean


def _norm(merchant: str) -> str:
    return merchant.strip().lower()


def detect_recurring_candidates(
    expenses: list[dict],
    existing_merchants: set[str],
    suppressed_merchants: set[str],
    *,
    tolerance: float = 0.10,
    min_months: int = 2,
) -> list[dict]:
    """
    `expenses`: list of dicts with keys `merchant` (str), `amount` (number),
    `spent_at` (datetime). Returns candidates as
    {merchant, amount, count, months} sorted by amount descending.
    """
    existing = {_norm(m) for m in existing_merchants}
    suppressed = {_norm(m) for m in suppressed_merchants}

    groups: dict[str, dict] = {}
    for e in expenses:
        merchant = e.get("merchant")
        if not merchant:
            continue
        key = _norm(merchant)
        if key in existing or key in suppressed:
            continue
        g = groups.setdefault(
            key, {"display": merchant.strip(), "amounts": [], "months": set()}
        )
        g["amounts"].append(float(e["amount"]))
        spent_at: datetime = e["spent_at"]
        g["months"].add((spent_at.year, spent_at.month))

    candidates: list[dict] = []
    for g in groups.values():
        if len(g["months"]) < min_months:
            continue
        amounts = g["amounts"]
        avg = mean(amounts)
        if avg <= 0:
            continue
        # All amounts must be within ±tolerance of the mean
        if any(abs(a - avg) / avg > tolerance for a in amounts):
            continue
        candidates.append(
            {
                "merchant": g["display"],
                "amount": round(Decimal(str(avg)), 2),
                "count": len(amounts),
                "months": len(g["months"]),
            }
        )

    candidates.sort(key=lambda c: c["amount"], reverse=True)
    return candidates
