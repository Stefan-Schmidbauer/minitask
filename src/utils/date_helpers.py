import calendar
from datetime import date, datetime, timedelta

COLOR_OVERDUE = "#d9534f"
COLOR_TODAY = "#000000"
COLOR_FUTURE = "#337ab7"
COLOR_STARRED = "#8e44ad"


def get_date_class(date_str: str) -> str:
    if not date_str:
        return ""
    today = date.today().isoformat()
    if date_str < today:
        return "overdue"
    if date_str > today:
        return "future"
    return "today"


def get_date_color(date_str: str) -> str:
    cls = get_date_class(date_str)
    if cls == "overdue":
        return COLOR_OVERDUE
    if cls == "future":
        return COLOR_FUTURE
    return COLOR_TODAY


def format_date_display(iso_date: str) -> str:
    if not iso_date:
        return ""
    try:
        parts = iso_date.split("-")
        return f"{parts[2]}.{parts[1]}.{parts[0]}"
    except (IndexError, ValueError):
        return iso_date


def increment_date(iso_date: str, days: int = 1) -> str:
    if not iso_date:
        return date.today().isoformat()
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
        return (d + timedelta(days=days)).isoformat()
    except ValueError:
        return date.today().isoformat()


def increment_month(iso_date: str) -> str:
    if not iso_date:
        return date.today().isoformat()
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
        year = d.year + (d.month // 12)
        month = (d.month % 12) + 1
        max_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(d.day, max_day)).isoformat()
    except ValueError:
        return date.today().isoformat()


def today_iso() -> str:
    return date.today().isoformat()
