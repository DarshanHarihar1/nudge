from decimal import Decimal


def compute_reconciliation(
    opening: Decimal,
    closing: Decimal,
    logged_total: Decimal,
    recurring_debit: Decimal,
    recurring_credit: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Returns (expected_close, discrepancy).

    expected_close = opening - logged_total - recurring_debit + recurring_credit
    discrepancy    = expected_close - closing
      positive → unaccounted outflow (user spent more than logged)
      negative → surplus vs expectation (e.g. unlisted income)
    """
    expected_close = opening - logged_total - recurring_debit + recurring_credit
    discrepancy = expected_close - closing
    return expected_close, discrepancy


def classify_discrepancy(
    discrepancy: Decimal,
    *,
    balanced_under: Decimal = Decimal("100"),
    gap_under: Decimal = Decimal("1000"),
) -> str:
    """Bucket a reconciliation discrepancy into a status label."""
    mag = abs(discrepancy)
    if mag < balanced_under:
        return "balanced"
    if mag < gap_under:
        return "gap"
    return "large_gap"
