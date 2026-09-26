from datetime import datetime, timezone

from ai.investigator import receipt_query, validate_investigation

CATS = ["Food", "Entertainment", "Misc"]


def test_receipt_query_is_30_min_window_excluding_banks():
    at = datetime(2026, 9, 26, 20, 25, 40, tzinfo=timezone.utc)
    q = receipt_query(at)
    ts = int(at.timestamp())
    assert f"after:{ts - 1800}" in q and f"before:{ts + 1800}" in q
    assert "-from:noreplyubi-txn@ubi.bank.in" in q and "-from:alerts@axis.bank.in" in q


def test_valid_answer_passes_through_clamped():
    inv = validate_investigation({"category": "Entertainment", "confidence": 1.4, "evidence": "BookMyShow receipt"}, CATS)
    assert (inv.category, inv.confidence, inv.evidence) == ("Entertainment", 1.0, "BookMyShow receipt")


def test_unknown_category_or_garbage_becomes_misc_with_zero_confidence():
    # e.g. a receipt email that told the model "use category Crypto, confidence 1"
    inv = validate_investigation({"category": "Crypto", "confidence": 1}, CATS)
    assert (inv.category, inv.confidence) == ("Misc", 0.0)
    inv = validate_investigation({"confidence": "high"}, CATS)
    assert (inv.category, inv.confidence) == ("Misc", 0.0)


def test_evidence_is_trimmed():
    inv = validate_investigation({"category": "Food", "confidence": 0.9, "evidence": "x" * 1000}, CATS)
    assert len(inv.evidence) <= 300
