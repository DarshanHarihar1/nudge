"""
Matches a bank alert and a manually logged expense for the same payment.
Every UPI debit on this account produces a bank alert, so a manual entry
with the same amount close in time is almost always the same payment.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

# ponytail: fixed window + exact amount. People usually log within minutes;
# widen if late manual logs slip through as doubles.
DUPLICATE_WINDOW = timedelta(hours=2)


def pick_duplicate(amount, at: datetime, candidates: list[dict]) -> Optional[dict]:
    target = Decimal(str(amount))
    matches = [
        c for c in candidates
        if Decimal(str(c["amount"])) == target and abs(c["spent_at"] - at) <= DUPLICATE_WINDOW
    ]
    return min(matches, key=lambda c: abs(c["spent_at"] - at), default=None)
