from datetime import datetime, timezone
from decimal import Decimal

from services.digest import format_digest_line


def test_line_has_amount_payee_time_and_note():
    line = format_digest_line({
        "amount": Decimal("1.00"), "merchant": "AJAYKUMA",
        "spent_at": datetime(2026, 9, 26, 20, 25, tzinfo=timezone.utc),
        "note": "No receipt found; first payment to this person.",
    }, "INR")
    assert "AJAYKUMA" in line and "01:55" in line  # shown in IST
    assert "No receipt found" in line


def test_line_without_note():
    line = format_digest_line({
        "amount": Decimal("50"), "merchant": None,
        "spent_at": datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc), "note": None,
    }, "INR")
    assert "unknown payee" in line
