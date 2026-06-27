import pytest
from utils.balance_parser import parse_balance


@pytest.mark.parametrize("text,expected", [
    ("48200", 48200.0),
    ("48,200", 48200.0),
    ("₹48200", 48200.0),
    ("₹48,200", 48200.0),
    ("48k", 48000.0),
    ("48K", 48000.0),
    ("48.5k", 48500.0),
    (" 1000 ", 1000.0),
    ("0", 0.0),
])
def test_parse_valid(text, expected):
    assert parse_balance(text) == expected


@pytest.mark.parametrize("text", [
    "hello",
    "",
    "abc123",
    "transfer done",
    "check balance",
])
def test_parse_invalid(text):
    assert parse_balance(text) is None
