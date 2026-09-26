import pytest

from services.email_ingest import _parse_spent_at, decide_route


@pytest.mark.parametrize("confidence,amount,from_memory,expected", [
    (1.0, 50_000, True, "auto"),      # remembered payee, any amount
    (0.8, 100, False, "auto"),        # boundary: 0.8 is confident
    (0.79, 100, False, "ask_later"),
    (0.5, 4999.99, False, "ask_later"),
    (0.5, 5000, False, "ask_now"),    # big and unsure: ask right away
])
def test_decide_route(confidence, amount, from_memory, expected):
    assert decide_route(confidence, amount, from_memory) == expected


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
