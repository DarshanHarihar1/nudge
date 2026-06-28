import hashlib
import hmac
import time

from utils.telegram_auth import verify_telegram_login

BOT_TOKEN = "123456:test-bot-token"


def _sign(data: dict, bot_token: str = BOT_TOKEN) -> dict:
    pairs = [f"{k}={v}" for k, v in data.items()]
    data_check_string = "\n".join(sorted(pairs))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return {**data, "hash": h}


def test_valid_signature_passes():
    data = _sign({"id": "858244316", "first_name": "D", "auth_date": str(int(time.time()))})
    assert verify_telegram_login(data, BOT_TOKEN) is True


def test_tampered_data_fails():
    data = _sign({"id": "858244316", "first_name": "D", "auth_date": str(int(time.time()))})
    data["id"] = "999999"  # tamper after signing
    assert verify_telegram_login(data, BOT_TOKEN) is False


def test_missing_hash_fails():
    assert verify_telegram_login({"id": "1", "auth_date": str(int(time.time()))}, BOT_TOKEN) is False


def test_wrong_bot_token_fails():
    data = _sign({"id": "1", "auth_date": str(int(time.time()))})
    assert verify_telegram_login(data, "different-token") is False


def test_stale_auth_date_fails():
    old = str(int(time.time()) - 100_000)
    data = _sign({"id": "1", "auth_date": old})
    assert verify_telegram_login(data, BOT_TOKEN, max_age_seconds=86_400) is False
