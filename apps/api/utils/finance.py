"""Pure financial calculations."""
from __future__ import annotations

from decimal import Decimal


def savings_rate(income: Decimal, expenses: Decimal) -> float | None:
    """
    (income - expenses) / income.
    Returns None when income is zero/negative (cannot be meaningfully computed).
    """
    if income <= 0:
        return None
    return float((income - expenses) / income)
