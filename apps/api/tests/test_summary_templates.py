from decimal import Decimal

from utils.summary_templates import (
    build_monthly_summary,
    build_weekly_summary,
    format_nl_answer,
)


def test_weekly_summary_contains_totals_and_categories():
    text = build_weekly_summary(
        total_spend=Decimal("4200"),
        top_categories=[
            {"name": "Food", "emoji": "🍴", "amount": Decimal("2000")},
            {"name": "Transport", "emoji": "🚗", "amount": Decimal("1200")},
        ],
        over_budget=[{"name": "Food", "emoji": "🍴", "pct": 84.0}],
    )
    assert "Weekly Summary" in text
    assert "₹4,200" in text
    assert "🍴 Food" in text
    assert "84%" in text


def test_monthly_summary_contains_totals_and_categories():
    text = build_monthly_summary(
        total_spend=Decimal("30000"),
        top_categories=[{"name": "Rent", "emoji": "🏠", "amount": Decimal("18000")}],
        over_budget=[],
    )
    assert "Monthly Summary" in text
    assert "₹30,000" in text
    assert "🏠 Rent" in text


def test_summaries_omit_balance_concepts():
    text = build_monthly_summary(
        total_spend=Decimal("30000"),
        top_categories=[],
        over_budget=[],
    )
    assert "Savings rate" not in text
    assert "Reconciliation" not in text


def test_format_nl_total_spend():
    out = format_nl_answer("totalSpend", {"range": "month"}, [{"total": 4200}])
    assert "₹4,200" in out and "month" in out


def test_format_nl_sum_by_one_category():
    out = format_nl_answer(
        "sumByCategory", {"range": "month", "category": "Food"}, [{"amount": 2000}]
    )
    assert "Food" in out and "₹2,000" in out


def test_format_nl_top_merchants():
    out = format_nl_answer(
        "topMerchants",
        {"range": "last_week"},
        [{"merchant": "Swiggy", "amount": 800, "count": 3}],
    )
    assert "Swiggy" in out and "₹800" in out and "×3" in out


def test_format_nl_count():
    out = format_nl_answer("countExpenses", {"range": "today"}, [{"count": 5}])
    assert "5" in out
