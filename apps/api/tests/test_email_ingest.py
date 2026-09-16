import pytest

from services.email_ingest import needs_recategorize, _parse_spent_at


@pytest.mark.parametrize("confidence,expected", [
    (0.0, True),
    (0.59, True),
    (0.6, False),
    (0.61, False),
    (1.0, False),
])
def test_needs_recategorize(confidence, expected):
    assert needs_recategorize(confidence) is expected


def test_parse_spent_at_valid():
    result = _parse_spent_at("16-09-2026 22:11:19")
    assert result is not None
    assert result.year == 2026
    assert result.month == 9
    assert result.day == 16
    assert result.hour == 22
    assert result.minute == 11
    assert result.second == 19
    assert result.tzinfo is not None


def test_parse_spent_at_invalid():
    assert _parse_spent_at("not a date") is None
    assert _parse_spent_at("") is None
