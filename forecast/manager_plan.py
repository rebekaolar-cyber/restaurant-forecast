"""The manager's own weekly plan: the same guest number for each weekday, every week.

This is the benchmark. Every backtest reports it next to our forecast, and our forecast has to
beat it. It is not used to make the forecast.
"""

from __future__ import annotations

from datetime import date

# Monday = 0 ... Sunday = 6, as Python counts weekdays.
GUESTS_BY_WEEKDAY = {
    0: 100,  # Monday
    1: 100,  # Tuesday
    2: 100,  # Wednesday
    3: 120,  # Thursday
    4: 250,  # Friday
    5: 300,  # Saturday
    6: 180,  # Sunday
}

# One real number from the restaurant's reservation book: on Friday 9 October 2026 it held
# 47 reservations for 174 people, walk-ins included. The plan says 250 for a Friday.
REAL_FRIDAY_RESERVATIONS = 47
REAL_FRIDAY_GUESTS = 174


def planned_guests(day: date) -> int:
    return GUESTS_BY_WEEKDAY[day.weekday()]
