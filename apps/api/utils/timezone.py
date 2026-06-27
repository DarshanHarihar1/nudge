from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def today_ist() -> date:
    return now_ist().date()


def current_month_str() -> str:
    """Returns 'YYYY-MM' for the current IST month, used for alert deduplication."""
    return now_ist().strftime("%Y-%m")
