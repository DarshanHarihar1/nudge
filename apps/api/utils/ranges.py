"""IST-aware date range resolution for analytics and NL queries."""
from __future__ import annotations

from datetime import datetime, timedelta

from utils.timezone import IST, now_ist


def _ist_midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _add_months(dt: datetime, months: int) -> datetime:
    """Shift a datetime by a whole number of months, clamping the day."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp day to the last valid day of the target month
    next_month = datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=dt.tzinfo)
    last_day = (next_month - timedelta(days=1)).day
    return dt.replace(year=year, month=month, day=min(dt.day, last_day))


# Range keywords accepted from NL queries and the dashboard period selector.
RANGE_KEYWORDS = {
    "today",
    "yesterday",
    "week",
    "last_week",
    "month",
    "last_month",
    "last_3_months",
    "year",
    "all",
}


def resolve_range(keyword: str, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    """
    Map a range keyword to (start, end) as timezone-aware IST datetimes.
    `end` is exclusive. Unknown keywords default to the current month.
    """
    now = now or now_ist()
    today0 = _ist_midnight(now)

    if keyword == "today":
        return today0, today0 + timedelta(days=1)
    if keyword == "yesterday":
        return today0 - timedelta(days=1), today0
    if keyword == "week":
        # Monday-anchored current week
        start = today0 - timedelta(days=now.weekday())
        return start, start + timedelta(days=7)
    if keyword == "last_week":
        start = today0 - timedelta(days=now.weekday() + 7)
        return start, start + timedelta(days=7)
    if keyword == "last_month":
        this_month_start = today0.replace(day=1)
        last_month_start = _add_months(this_month_start, -1)
        return last_month_start, this_month_start
    if keyword == "last_3_months":
        this_month_start = today0.replace(day=1)
        return _add_months(this_month_start, -3), this_month_start + _month_len(this_month_start)
    if keyword == "year":
        start = today0.replace(month=1, day=1)
        return start, start.replace(year=start.year + 1)
    if keyword == "all":
        return datetime(1970, 1, 1, tzinfo=IST), now + timedelta(days=1)

    # Default: current calendar month
    start = today0.replace(day=1)
    return start, start + _month_len(start)


def _month_len(month_start: datetime) -> timedelta:
    nxt = _add_months(month_start, 1)
    return nxt - month_start


def parse_custom_range(
    from_str: str | None, to_str: str | None, *, now: datetime | None = None
) -> tuple[datetime, datetime]:
    """
    Parse explicit from/to ISO dates (YYYY-MM-DD) into an IST range.
    Falls back to the current month if neither is provided.
    `to` is treated as inclusive of the whole day → end is to+1day exclusive.
    """
    if not from_str and not to_str:
        return resolve_range("month", now=now)

    now = now or now_ist()
    if from_str:
        start = datetime.fromisoformat(from_str).replace(tzinfo=IST)
        start = _ist_midnight(start)
    else:
        start = datetime(1970, 1, 1, tzinfo=IST)

    if to_str:
        end = datetime.fromisoformat(to_str).replace(tzinfo=IST)
        end = _ist_midnight(end) + timedelta(days=1)
    else:
        end = _ist_midnight(now) + timedelta(days=1)

    return start, end
