"""
Telegram Login Widget signature verification.

https://core.telegram.org/widgets/login#checking-authorization
  secret_key        = SHA256(bot_token)
  data_check_string = "\\n".join(sorted("key=value" for k,v in data if k != "hash"))
  valid             = hmac_sha256(secret_key, data_check_string) == data["hash"]
"""
from __future__ import annotations

import hashlib
import hmac
import time


def verify_telegram_login(
    data: dict[str, str],
    bot_token: str,
    *,
    max_age_seconds: int = 86_400,
    now: float | None = None,
) -> bool:
    """
    Returns True only if the widget payload is authentic and fresh.
    `data` is the raw query/body dict from the widget callback (strings).
    """
    received_hash = data.get("hash")
    if not received_hash:
        return False

    pairs = [f"{k}={v}" for k, v in data.items() if k != "hash"]
    data_check_string = "\n".join(sorted(pairs))

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        return False

    # Reject stale logins (replay protection)
    auth_date = data.get("auth_date")
    if auth_date is not None:
        now = now if now is not None else time.time()
        try:
            if now - int(auth_date) > max_age_seconds:
                return False
        except (TypeError, ValueError):
            return False

    return True
