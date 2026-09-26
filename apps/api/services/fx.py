"""Foreign-currency card spends → INR, since every total sums raw amounts."""
from typing import Optional

import httpx

# Free, keyless ECB reference rates. ponytail: the day's reference rate, not
# the bank's marked-up rate — close enough for tracking; the original amount
# is kept in the expense note.
FX_URL = "https://api.frankfurter.dev/v1/latest"


async def to_inr(amount: float, currency: str) -> Optional[float]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(FX_URL, params={"base": currency, "symbols": "INR"})
            r.raise_for_status()
            return round(amount * r.json()["rates"]["INR"], 2)
    except Exception:
        return None
