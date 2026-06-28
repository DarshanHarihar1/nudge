from ai.nl_query import validate_mapping


def test_valid_total_spend():
    m = validate_mapping({"function": "totalSpend", "params": {"range": "month"}})
    assert m == {"function": "totalSpend", "params": {"range": "month"}}


def test_sum_by_category_with_category():
    m = validate_mapping(
        {"function": "sumByCategory", "params": {"range": "month", "category": "Food"}}
    )
    assert m["function"] == "sumByCategory"
    assert m["params"]["category"] == "Food"


def test_invalid_category_dropped():
    m = validate_mapping(
        {"function": "sumByCategory", "params": {"range": "week", "category": "Nonsense"}}
    )
    assert "category" not in m["params"]


def test_top_merchants_limit_clamped():
    assert validate_mapping({"function": "topMerchants", "params": {"limit": 999}})["params"]["limit"] == 20
    assert validate_mapping({"function": "topMerchants", "params": {"limit": 0}})["params"]["limit"] == 1


def test_unknown_range_defaults_to_month():
    m = validate_mapping({"function": "totalSpend", "params": {"range": "fortnight"}})
    assert m["params"]["range"] == "month"


def test_function_not_in_allowlist_rejected():
    assert validate_mapping({"function": "dropTable", "params": {}}) is None
    assert validate_mapping({"function": "rawSQL", "params": {"range": "month"}}) is None


def test_malformed_input_rejected():
    assert validate_mapping(None) is None
    assert validate_mapping({}) is None
    assert validate_mapping({"function": "totalSpend", "params": "oops"}) is None


def test_missing_params_defaults():
    m = validate_mapping({"function": "totalSpend"})
    assert m["params"]["range"] == "month"
