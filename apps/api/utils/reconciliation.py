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
