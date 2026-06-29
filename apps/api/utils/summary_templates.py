"""
Template-based summary text builders (no LLM).
Kept pure so they're trivially unit-testable.
"""
from __future__ import annotations

from decimal import Decimal


def _fmt(amount: Decimal | float | int, currency: str = "INR") -> str:
    num = float(amount)
    if currency == "INR":
        return f"₹{int(round(num)):,}"
    return f"{num:,.2f} {currency}"


def build_weekly_summary(
    *,
    total_spend: Decimal,
    top_categories: list[dict],  # {name, emoji, amount}
    over_budget: list[dict],  # {name, emoji, pct}
    insight: str | None = None,
    currency: str = "INR",
) -> str:
    lines = ["📅 *Weekly Summary*", "", f"Total spent: {_fmt(total_spend, currency)}"]

    if top_categories:
        lines.append("")
        lines.append("Top categories:")
        for c in top_categories[:3]:
            lines.append(f"  {c['emoji']} {c['name']}: {_fmt(c['amount'], currency)}")

    if over_budget:
        lines.append("")
        lines.append("⚠️ Over 80% of budget:")
        for c in over_budget:
            lines.append(f"  {c['emoji']} {c['name']} ({c['pct']:.0f}%)")

    if insight:
        lines.append("")
        lines.append(f"💡 {insight}")

    return "\n".join(lines)


def build_monthly_summary(
    *,
    total_spend: Decimal,
    top_categories: list[dict],
    over_budget: list[dict],
    insight: str | None = None,
    currency: str = "INR",
) -> str:
    lines = ["🗓 *Monthly Summary*", "", f"Total spent: {_fmt(total_spend, currency)}"]

    if top_categories:
        lines.append("")
        lines.append("Top categories:")
        for c in top_categories[:3]:
            lines.append(f"  {c['emoji']} {c['name']}: {_fmt(c['amount'], currency)}")

    if over_budget:
        lines.append("")
        lines.append("⚠️ Over 80% of budget:")
        for c in over_budget:
            lines.append(f"  {c['emoji']} {c['name']} ({c['pct']:.0f}%)")

    if insight:
        lines.append("")
        lines.append(f"💡 {insight}")

    return "\n".join(lines)


def format_nl_answer(function: str, params: dict, rows: list[dict], currency: str = "INR") -> str:
    """Render the result of an NL query into a human-readable Telegram message."""
    rng = params.get("range", "month").replace("_", " ")

    if function == "totalSpend":
        total = rows[0]["total"] if rows else 0
        return f"You spent {_fmt(total, currency)} ({rng})."

    if function == "countExpenses":
        count = rows[0]["count"] if rows else 0
        return f"You logged {count} expense(s) ({rng})."

    if function == "sumByCategory":
        cat = params.get("category")
        if cat:
            total = rows[0]["amount"] if rows else 0
            return f"{cat} spending ({rng}): {_fmt(total, currency)}."
        if not rows:
            return f"No spending recorded ({rng})."
        lines = [f"Spending by category ({rng}):"]
        for r in rows:
            lines.append(f"  {r.get('emoji','')} {r['name']}: {_fmt(r['amount'], currency)}")
        return "\n".join(lines)

    if function == "topMerchants":
        if not rows:
            return f"No merchant activity ({rng})."
        lines = [f"Top merchants ({rng}):"]
        for r in rows:
            lines.append(f"  {r['merchant']}: {_fmt(r['amount'], currency)} ×{r['count']}")
        return "\n".join(lines)

    return "No results."
