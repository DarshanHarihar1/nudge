import base64

from services.gmail_sync import extract_body, header
from tests.test_email_parser import REAL_CAPTURED_EMAIL
from utils.email_parser import parse_ubi_debit_email


def _b64(text: str) -> str:
    # Gmail API returns unpadded base64url
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_real_alert_survives_gmail_multipart_encoding():
    payload = {
        "mimeType": "multipart/alternative",
        "headers": [
            {"name": "From", "value": "UBI <noreplyubi-txn@ubi.bank.in>"},
            {"name": "Subject", "value": "DEBIT TRANSACTION ALERT"},
        ],
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("plain fallback")}},
            {"mimeType": "text/html", "body": {"data": _b64(REAL_CAPTURED_EMAIL)}},
        ],
    }
    parsed = parse_ubi_debit_email(extract_body(payload))
    assert parsed is not None
    assert parsed.payee == "ZOMATO"
    assert parsed.amount == 97.84
    assert parsed.rrn == "561297249109"
    assert header(payload, "from") == "UBI <noreplyubi-txn@ubi.bank.in>"
    assert header(payload, "Subject") == "DEBIT TRANSACTION ALERT"


def test_single_part_and_nested_bodies():
    assert extract_body({"mimeType": "text/html", "body": {"data": _b64("<b>hi</b>")}}) == "<b>hi</b>"
    nested = {"mimeType": "multipart/mixed", "parts": [
        {"mimeType": "multipart/alternative", "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("only plain")}},
        ]},
        {"mimeType": "application/pdf", "body": {"attachmentId": "x"}},
    ]}
    assert extract_body(nested) == "only plain"


def test_missing_body_and_header():
    assert extract_body({"mimeType": "multipart/mixed", "parts": []}) == ""
    assert header({}, "From") == ""
