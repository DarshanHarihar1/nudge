from datetime import datetime
from decimal import Decimal

from utils.detection import detect_recurring_candidates


def _exp(merchant, amount, year, month, day=5):
    return {"merchant": merchant, "amount": amount, "spent_at": datetime(year, month, day)}


def test_detects_three_month_pattern():
    expenses = [
        _exp("Netflix", 649, 2026, 4),
        _exp("Netflix", 649, 2026, 5),
        _exp("Netflix", 649, 2026, 6),
    ]
    out = detect_recurring_candidates(expenses, set(), set())
    assert len(out) == 1
    assert out[0]["merchant"] == "Netflix"
    assert out[0]["amount"] == Decimal("649.00")
    assert out[0]["months"] == 3


def test_one_off_not_flagged():
    expenses = [_exp("RandomShop", 1200, 2026, 6)]
    assert detect_recurring_candidates(expenses, set(), set()) == []


def test_two_in_same_month_not_flagged():
    # Two charges, but same month → only 1 distinct month
    expenses = [_exp("Gym", 500, 2026, 6, 2), _exp("Gym", 500, 2026, 6, 20)]
    assert detect_recurring_candidates(expenses, set(), set()) == []


def test_variable_amount_not_flagged():
    # Electricity bill varies wildly → outside ±10% tolerance
    expenses = [
        _exp("Electricity", 800, 2026, 4),
        _exp("Electricity", 2000, 2026, 5),
        _exp("Electricity", 1200, 2026, 6),
    ]
    assert detect_recurring_candidates(expenses, set(), set()) == []


def test_within_tolerance_flagged():
    expenses = [
        _exp("Spotify", 119, 2026, 5),
        _exp("Spotify", 125, 2026, 6),  # ~5% diff, within 10%
    ]
    out = detect_recurring_candidates(expenses, set(), set())
    assert len(out) == 1


def test_existing_recurring_skipped():
    expenses = [_exp("Netflix", 649, 2026, 5), _exp("Netflix", 649, 2026, 6)]
    assert detect_recurring_candidates(expenses, {"Netflix"}, set()) == []


def test_suppressed_skipped():
    expenses = [_exp("Netflix", 649, 2026, 5), _exp("Netflix", 649, 2026, 6)]
    assert detect_recurring_candidates(expenses, set(), {"netflix"}) == []  # case-insensitive
