from decimal import Decimal
import pytest
from utils.reconciliation import compute_reconciliation as _compute_reconciliation


def dec(*args):
    return tuple(Decimal(str(x)) for x in args)


def test_zero_discrepancy():
    opening, closing, logged, rec_d, rec_c = dec(50000, 32000, 18000, 0, 0)
    expected_close, discrepancy = _compute_reconciliation(opening, closing, logged, rec_d, rec_c)
    assert expected_close == Decimal("32000")
    assert discrepancy == Decimal("0")


def test_unaccounted_spend():
    # User spent 2300 that wasn't logged
    opening, closing, logged, rec_d, rec_c = dec(50000, 44500, 3200, 0, 0)
    expected_close, discrepancy = _compute_reconciliation(opening, closing, logged, rec_d, rec_c)
    assert expected_close == Decimal("46800")
    assert discrepancy == Decimal("2300")  # positive = unaccounted outflow


def test_surplus_over_expected():
    # Balance is higher than expected — surplus
    opening, closing, logged, rec_d, rec_c = dec(50000, 49000, 500, 0, 0)
    expected_close, discrepancy = _compute_reconciliation(opening, closing, logged, rec_d, rec_c)
    assert expected_close == Decimal("49500")
    assert discrepancy == Decimal("500")


def test_recurring_debit_included():
    # 15000 rent (recurring debit) + 3000 manual expenses
    opening, closing, logged, rec_d, rec_c = dec(50000, 32000, 3000, 15000, 0)
    expected_close, discrepancy = _compute_reconciliation(opening, closing, logged, rec_d, rec_c)
    assert expected_close == Decimal("32000")
    assert discrepancy == Decimal("0")


def test_recurring_credit_offsets():
    # 50000 salary credit, 5000 expenses
    opening, closing, logged, rec_d, rec_c = dec(10000, 55000, 5000, 0, 50000)
    expected_close, discrepancy = _compute_reconciliation(opening, closing, logged, rec_d, rec_c)
    assert expected_close == Decimal("55000")
    assert discrepancy == Decimal("0")


def test_negative_discrepancy_overspend():
    # Somehow balance is higher than expected (income not logged)
    opening, closing, logged, rec_d, rec_c = dec(30000, 35000, 1000, 0, 0)
    expected_close, discrepancy = _compute_reconciliation(opening, closing, logged, rec_d, rec_c)
    assert expected_close == Decimal("29000")
    assert discrepancy == Decimal("-6000")  # negative = surplus vs expectation
