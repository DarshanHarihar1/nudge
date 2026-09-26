from datetime import datetime, timedelta, timezone
from decimal import Decimal

from services.dedupe import pick_duplicate

T = datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc)


def row(amount, minutes, id_):
    return {"id": id_, "amount": Decimal(str(amount)), "spent_at": T + timedelta(minutes=minutes)}


def test_same_amount_within_window_matches():
    assert pick_duplicate(219.29, T, [row(219.29, 20, "a")])["id"] == "a"


def test_different_amount_or_outside_window_does_not_match():
    assert pick_duplicate(219.29, T, [row(219.30, 5, "a"), row(219.29, 121, "b")]) is None


def test_closest_in_time_wins_when_two_match():
    got = pick_duplicate(20, T, [row(20, -90, "far"), row(20, 10, "near")])
    assert got["id"] == "near"


def test_no_candidates():
    assert pick_duplicate(20, T, []) is None
