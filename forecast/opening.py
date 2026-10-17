"""Which evenings the restaurant is open.

Open every day for dinner, except Mondays before 10 August 2026: the restaurant only started
opening on Mondays then (confirmed by Rebeka on 10 Oct 2026, and visible in TheFork Manager as
the separate service "Maandag vanaf 10 augustus").

A closed evening has no guests at all. It is not a quiet evening, so it must never be counted
as "0 guests" in an average or a backtest.
"""

from __future__ import annotations

from datetime import date

MONDAYS_OPEN_FROM = date(2026, 8, 10)


def is_open(day: date) -> bool:
    return day.weekday() != 0 or day >= MONDAYS_OPEN_FROM
