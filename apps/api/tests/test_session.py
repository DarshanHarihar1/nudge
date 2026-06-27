import time

from utils.session import sign_session, verify_session

SECRET = "test-secret-key"


def test_roundtrip():
    token = sign_session(858244316, SECRET)
    assert verify_session(token, SECRET) == 858244316


def test_wrong_secret_fails():
    token = sign_session(858244316, SECRET)
    assert verify_session(token, "other-secret") is None


def test_tampered_payload_fails():
    token = sign_session(858244316, SECRET)
    payload, sig = token.split(".")
    tampered = "abcd" + payload[4:] + "." + sig
    assert verify_session(tampered, SECRET) is None


def test_expired_token_fails():
    token = sign_session(858244316, SECRET, ttl_seconds=-1)
    assert verify_session(token, SECRET) is None


def test_garbage_token_fails():
    assert verify_session("not-a-token", SECRET) is None
    assert verify_session("", SECRET) is None


def test_future_expiry_passes():
    token = sign_session(1, SECRET, ttl_seconds=3600)
    assert verify_session(token, SECRET, now=time.time()) == 1
