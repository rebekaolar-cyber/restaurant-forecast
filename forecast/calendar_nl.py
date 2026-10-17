"""Dutch public holidays and a few special evenings, worked out from the date alone.

No downloads and no extra library: Easter is calculated, the rest follows from it or is fixed.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache


def easter_sunday(year: int) -> date:
    """Easter Sunday in the Gregorian calendar (the "anonymous" algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


@lru_cache(maxsize=None)
def public_holidays(year: int) -> dict[date, str]:
    """The official Dutch public holidays of one year: {day: name}."""
    easter = easter_sunday(year)
    kings_day = date(year, 4, 27)
    if kings_day.weekday() == 6:  # on a Sunday it is celebrated the day before
        kings_day = date(year, 4, 26)
    return {
        date(year, 1, 1): "new_years_day",
        easter - timedelta(days=2): "good_friday",
        easter: "easter_sunday",
        easter + timedelta(days=1): "easter_monday",
        kings_day: "kings_day",
        date(year, 5, 5): "liberation_day",
        easter + timedelta(days=39): "ascension_day",
        easter + timedelta(days=49): "whit_sunday",
        easter + timedelta(days=50): "whit_monday",
        date(year, 12, 25): "christmas_day",
        date(year, 12, 26): "boxing_day",
    }


@lru_cache(maxsize=None)
def special_evenings(year: int) -> dict[date, str]:
    """Evenings that are not public holidays but matter to a restaurant: {day: name}."""
    return {
        date(year, 2, 14): "valentines_day",
        _nth_sunday(year, 5, 2): "mothers_day",
        date(year, 12, 5): "sinterklaas",
        date(year, 12, 24): "christmas_eve",
        date(year, 12, 31): "new_years_eve",
    }


def holiday_name(day: date) -> str | None:
    """The name of the public holiday on this day, or None."""
    return public_holidays(day.year).get(day)


def special_name(day: date) -> str | None:
    """The name of the special evening on this day, or None."""
    return special_evenings(day.year).get(day)


def is_ordinary(day: date) -> bool:
    """True for a day that is neither a public holiday nor a special evening."""
    return holiday_name(day) is None and special_name(day) is None
