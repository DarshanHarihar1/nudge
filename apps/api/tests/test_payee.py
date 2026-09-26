from utils.payee import normalize_payee


def test_normalize_collapses_case_and_whitespace():
    assert normalize_payee("  ZOMATO   L ") == "zomato l"
    assert normalize_payee("Zomato") == "zomato"


def test_normalize_empty_is_none():
    assert normalize_payee(None) is None
    assert normalize_payee("   ") is None
