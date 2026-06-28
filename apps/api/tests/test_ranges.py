from datetime import datetime

from utils.timezone import IST
from utils.ranges import resolve_range, parse_custom_range


# Reference "now": Wednesday, 2026-06-17 14:30 IST
NOW = datetime(2026, 6, 17, 14, 30, tzinfo=IST)


def test_today():
    start, end = resolve_range("today", now=NOW)
    assert start == datetime(2026, 6, 17, tzinfo=IST)
    assert end == datetime(2026, 6, 18, tzinfo=IST)


def test_month():
    start, end = resolve_range("month", now=NOW)
    assert start == datetime(2026, 6, 1, tzinfo=IST)
    assert end == datetime(2026, 7, 1, tzinfo=IST)


def test_last_month():
    start, end = resolve_range("last_month", now=NOW)
    assert start == datetime(2026, 5, 1, tzinfo=IST)
    assert end == datetime(2026, 6, 1, tzinfo=IST)


def test_week_is_monday_anchored():
    # 2026-06-17 is a Wednesday → week starts Monday 2026-06-15
    start, end = resolve_range("week", now=NOW)
    assert start == datetime(2026, 6, 15, tzinfo=IST)
    assert end == datetime(2026, 6, 22, tzinfo=IST)


def test_last_3_months():
    start, end = resolve_range("last_3_months", now=NOW)
    assert start == datetime(2026, 3, 1, tzinfo=IST)
    assert end == datetime(2026, 7, 1, tzinfo=IST)


def test_unknown_defaults_to_month():
    start, end = resolve_range("decade", now=NOW)
    assert start == datetime(2026, 6, 1, tzinfo=IST)


def test_parse_custom_range_inclusive_end():
    start, end = parse_custom_range("2026-06-01", "2026-06-15", now=NOW)
    assert start == datetime(2026, 6, 1, tzinfo=IST)
    # end is exclusive → day after the 'to' date
    assert end == datetime(2026, 6, 16, tzinfo=IST)


def test_parse_custom_range_empty_defaults_to_month():
    start, end = parse_custom_range(None, None, now=NOW)
    assert start == datetime(2026, 6, 1, tzinfo=IST)
