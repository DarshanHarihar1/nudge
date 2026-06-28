"""
Stateless signed session tokens for the dashboard.

Token format:  base64url(payload_json).base64url(hmac_sha256(secret, payload))
Payload carries the telegram_id and an expiry timestamp. No server-side storage,
so it survives Render restarts and works on any instance.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def sign_session(telegram_id: int, secret: str, *, ttl_seconds: int = 86_400) -> str:
    payload = {"tid": telegram_id, "exp": int(time.time()) + ttl_seconds}
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).digest()
    return f"{_b64encode(payload_bytes)}.{_b64encode(sig)}"


def verify_session(token: str, secret: str, *, now: float | None = None) -> int | None:
    """Returns the telegram_id if the token is valid and unexpired, else None."""
    now = now if now is not None else time.time()
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload_bytes = _b64decode(payload_b64)
        expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(sig_b64)):
            return None
        payload = json.loads(payload_bytes)
    except (ValueError, KeyError, json.JSONDecodeError):
        return None

    if not isinstance(payload.get("tid"), int):
        return None
    if payload.get("exp", 0) < now:
        return None
    return payload["tid"]
