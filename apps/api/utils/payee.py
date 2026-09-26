"""Payee keys for category memory."""
from typing import Optional


def normalize_payee(merchant: Optional[str]) -> Optional[str]:
    # ponytail: exact match on a normalised name. Bank alerts truncate to ~8
    # chars ("ZOMATO L") while Telegram gets "Zomato", so each source learns
    # its own key; fuzzy matching if that proves annoying.
    if not merchant:
        return None
    key = " ".join(merchant.lower().split())
    return key or None
