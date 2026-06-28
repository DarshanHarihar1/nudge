from decimal import Decimal

from utils.finance import savings_rate
from utils.reconciliation import classify_discrepancy


def test_savings_rate_basic():
    assert savings_rate(Decimal("100000"), Decimal("68000")) == 0.32


def test_savings_rate_zero_income_is_none():
    assert savings_rate(Decimal("0"), Decimal("5000")) is None


def test_savings_rate_negative_income_is_none():
    assert savings_rate(Decimal("-10"), Decimal("5")) is None


def test_savings_rate_overspend_negative():
    assert savings_rate(Decimal("10000"), Decimal("12000")) == -0.2


def test_classify_balanced():
    assert classify_discrepancy(Decimal("50")) == "balanced"
    assert classify_discrepancy(Decimal("-99")) == "balanced"


def test_classify_gap():
    assert classify_discrepancy(Decimal("500")) == "gap"
    assert classify_discrepancy(Decimal("-999")) == "gap"


def test_classify_large_gap():
    assert classify_discrepancy(Decimal("2300")) == "large_gap"
    assert classify_discrepancy(Decimal("-5000")) == "large_gap"
