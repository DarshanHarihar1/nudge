import base64
import hashlib
import hmac
import time

from utils.composio_webhook import extract_trigger_slug, verify_composio_signature

SECRET = "whsec_test_secret_value"


def _sign(secret: str, webhook_id: str, webhook_timestamp: str, raw_body: bytes) -> str:
    signed_content = f"{webhook_id}.{webhook_timestamp}.".encode() + raw_body
    digest = hmac.new(secret.encode(), signed_content, hashlib.sha256).digest()
    return f"v1,{base64.b64encode(digest).decode()}"


def test_valid_signature_passes():
    body = b'{"hello":"world"}'
    ts = str(int(time.time()))
    sig = _sign(SECRET, "msg_1", ts, body)
    assert verify_composio_signature(SECRET, "msg_1", ts, body, sig) is True


def test_wrong_secret_fails():
    body = b'{"hello":"world"}'
    ts = str(int(time.time()))
    sig = _sign("some-other-secret", "msg_1", ts, body)
    assert verify_composio_signature(SECRET, "msg_1", ts, body, sig) is False


def test_tampered_body_fails():
    body = b'{"hello":"world"}'
    ts = str(int(time.time()))
    sig = _sign(SECRET, "msg_1", ts, body)
    assert verify_composio_signature(SECRET, "msg_1", ts, b'{"hello":"tampered"}', sig) is False


def test_stale_timestamp_fails():
    body = b'{"hello":"world"}'
    ts = str(int(time.time()) - 3600)  # 1 hour old
    sig = _sign(SECRET, "msg_1", ts, body)
    assert verify_composio_signature(SECRET, "msg_1", ts, body, sig) is False


def test_zero_tolerance_disables_staleness_check():
    body = b'{"hello":"world"}'
    ts = str(int(time.time()) - 3600)
    sig = _sign(SECRET, "msg_1", ts, body)
    assert verify_composio_signature(SECRET, "msg_1", ts, body, sig, tolerance_seconds=0) is True


def test_missing_headers_fail():
    body = b'{"hello":"world"}'
    ts = str(int(time.time()))
    sig = _sign(SECRET, "msg_1", ts, body)
    assert verify_composio_signature(SECRET, "", ts, body, sig) is False
    assert verify_composio_signature(SECRET, "msg_1", "", body, sig) is False
    assert verify_composio_signature(SECRET, "msg_1", ts, body, "") is False


def test_malformed_timestamp_fails():
    body = b'{"hello":"world"}'
    sig = _sign(SECRET, "msg_1", "not-a-number", body)
    assert verify_composio_signature(SECRET, "msg_1", "not-a-number", body, sig) is False


def test_extract_trigger_slug():
    envelope = {"metadata": {"trigger_slug": "GMAIL_NEW_GMAIL_MESSAGE"}}
    assert extract_trigger_slug(envelope) == "GMAIL_NEW_GMAIL_MESSAGE"


def test_extract_trigger_slug_missing():
    assert extract_trigger_slug({}) is None
