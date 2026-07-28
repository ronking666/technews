"""Standard Nasdaq trading-session calendar used for data validation."""

from datetime import date, timedelta

NASDAQ_HOLIDAY_SCHEDULE_URL = (
    "https://www.nasdaq.com/market-activity/stock-market-holiday-schedule"
)


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    """Return Gregorian Easter Sunday using the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = (h + ell - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _nearest_weekday(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _new_year_observed(year: int) -> date:
    day = date(year, 1, 1)
    return day + timedelta(days=1) if day.weekday() == 6 else day


def _standard_nasdaq_holidays(year: int) -> set[date]:
    holidays = {
        _new_year_observed(year),
        _nth_weekday(year, 1, weekday=0, occurrence=3),
        _nth_weekday(year, 2, weekday=0, occurrence=3),
        _easter_sunday(year) - timedelta(days=2),
        _last_weekday(year, 5, weekday=0),
        _nearest_weekday(date(year, 7, 4)),
        _nth_weekday(year, 9, weekday=0, occurrence=1),
        _nth_weekday(year, 11, weekday=3, occurrence=4),
        _nearest_weekday(date(year, 12, 25)),
    }
    if year >= 2022:
        holidays.add(_nearest_weekday(date(year, 6, 19)))
    return holidays


def expected_nasdaq_sessions(start: date, end: date) -> set[date]:
    """Return expected regular sessions in the half-open range ``[start, end)``."""
    if end <= start:
        return set()

    holidays: set[date] = set()
    for year in range(start.year, end.year + 1):
        holidays.update(_standard_nasdaq_holidays(year))

    sessions = set()
    current = start
    while current < end:
        if current.weekday() < 5 and current not in holidays:
            sessions.add(current)
        current += timedelta(days=1)
    return sessions
