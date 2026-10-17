"""Tests for the baseline forecast and the history it looks at, on a tiny hand-made restaurant.

The hand-made history: every Friday has 100 guests, and 40 of them were already in the book one
week before. So the "normal" Friday is easy to work out by hand.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from forecast.baseline import ForecastError, baseline_forecast, reference_days
from forecast.history import History, parse_moment, service_date

TZ = ZoneInfo("Europe/Amsterdam")
FRIDAY = date(2026, 10, 9)


def at(day: date, hour: int = 3, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)


def fridays_history(*, guests=100, booked_a_week_ahead=40, extra_bookings=()):
    """Twelve Fridays up to and including FRIDAY, each with the same guests and the same book."""
    guests_by_day, bookings = {}, []
    for weeks_back in range(12):
        day = FRIDAY - timedelta(days=7 * weeks_back)
        guests_by_day[day] = guests
        bookings.append((day, at(day - timedelta(days=10), 12), booked_a_week_ahead))   # booked 10 days ahead
        bookings.append((day, at(day - timedelta(days=1), 12), 30))                     # booked the day before
    return History(TZ, guests_by_day, bookings + list(extra_bookings))


# ---- the history ------------------------------------------------------------------------------


def test_a_table_after_midnight_belongs_to_the_evening_before():
    assert service_date(parse_moment("2026-10-10T22:30:00+00:00"), TZ) == date(2026, 10, 10)   # 00:30 on Sunday
    assert service_date(parse_moment("2026-10-10T15:00:00+00:00"), TZ) == date(2026, 10, 10)   # 17:00 on Saturday
    assert service_date(parse_moment("2026-10-11T04:30:00+00:00"), TZ) == date(2026, 10, 11)   # 06:30 on Sunday


def test_the_book_counts_only_bookings_made_by_that_moment():
    history = fridays_history()
    assert history.booked(FRIDAY, at(FRIDAY - timedelta(days=11))) == 0
    assert history.booked(FRIDAY, at(FRIDAY - timedelta(days=9))) == 40
    assert history.booked(FRIDAY, at(FRIDAY - timedelta(days=1), 12, 0)) == 70    # made at exactly that moment counts
    assert history.booked(FRIDAY, at(FRIDAY - timedelta(days=1), 11, 59)) == 40
    assert history.booked(date(2030, 1, 1), at(FRIDAY)) == 0


def test_history_from_rows_leaves_out_cancelled_bookings_and_adds_up_receipts():
    history = History.from_rows(
        TZ,
        [
            {"visit_date": "2026-10-09", "created_at": "2026-10-01T10:00:00+00:00", "party_size": 4, "status": "completed"},
            {"visit_date": "2026-10-09", "created_at": "2026-10-01T10:00:00+00:00", "party_size": 6, "status": "no_show"},
            {"visit_date": "2026-10-09", "created_at": "2026-10-01T10:00:00+00:00", "party_size": 8, "status": "cancelled"},
        ],
        [
            {"opened_at": "2026-10-09T16:00:00+00:00", "guests": 4},
            {"opened_at": "2026-10-09T22:30:00+00:00", "guests": 3},   # 00:30 on Saturday morning
            {"opened_at": "2026-10-10T16:00:00+00:00", "guests": 5},
        ],
    )
    assert history.booked(FRIDAY, at(FRIDAY)) == 10          # the no-show was in the book, the cancelled one is not
    assert history.guests(FRIDAY) == 7 and history.guests(date(2026, 10, 10)) == 5
    assert history.guests(date(2026, 10, 8)) is None


def test_a_timestamp_without_a_timezone_is_refused():
    with pytest.raises(ValueError, match="without a timezone"):
        parse_moment("2026-10-09T18:00:00")


# ---- the forecast -----------------------------------------------------------------------------


def test_the_average_of_the_same_weekday_over_the_last_six_weeks():
    history = fridays_history()
    next_friday = FRIDAY + timedelta(days=7)
    forecast = baseline_forecast(history, next_friday, at(FRIDAY + timedelta(days=1)))   # Saturday night
    assert forecast.weekday_average == 100
    assert forecast.reference_days == tuple(FRIDAY - timedelta(days=7 * n) for n in range(6))
    assert forecast.days_ahead == 7


def test_days_ahead_counts_the_evening_of_the_run_as_day_one():
    history = fridays_history()
    assert baseline_forecast(history, FRIDAY + timedelta(days=7), at(FRIDAY + timedelta(days=7))).days_ahead == 1
    assert baseline_forecast(history, FRIDAY + timedelta(days=7), at(FRIDAY - timedelta(days=6))).days_ahead == 14


def test_more_bookings_than_usual_raise_the_forecast_by_that_many():
    next_friday = FRIDAY + timedelta(days=7)
    usual = fridays_history(extra_bookings=[(next_friday, at(next_friday - timedelta(days=10), 12), 40)])
    busy = fridays_history(extra_bookings=[(next_friday, at(next_friday - timedelta(days=10), 12), 65)])
    quiet = fridays_history(extra_bookings=[(next_friday, at(next_friday - timedelta(days=10), 12), 20)])
    now = at(next_friday - timedelta(days=6))   # 7 days ahead: only the early bookings are in the book

    assert baseline_forecast(usual, next_friday, now).guests == 100
    assert (baseline_forecast(usual, next_friday, now).booked_now, baseline_forecast(usual, next_friday, now).booked_normally) == (40, 40)
    assert baseline_forecast(busy, next_friday, now).guests == 125     # 25 more booked than usual
    assert baseline_forecast(quiet, next_friday, now).guests == 80     # 20 fewer


def test_the_correction_is_kept_within_half_of_the_average():
    next_friday = FRIDAY + timedelta(days=7)
    wedding = fridays_history(extra_bookings=[(next_friday, at(next_friday - timedelta(days=10), 12), 240)])
    empty = fridays_history(guests=60)
    now = at(next_friday - timedelta(days=6))
    assert baseline_forecast(wedding, next_friday, now).guests == 150   # 100 + at most 50
    assert baseline_forecast(empty, next_friday, at(next_friday)).guests == 30    # 60 - at most 30


def test_bookings_made_later_do_not_change_an_earlier_forecast():
    next_friday = FRIDAY + timedelta(days=7)
    now = at(next_friday - timedelta(days=6))
    early = fridays_history(extra_bookings=[(next_friday, at(next_friday - timedelta(days=10), 12), 40)])
    with_late_rush = fridays_history(
        extra_bookings=[
            (next_friday, at(next_friday - timedelta(days=10), 12), 40),
            (next_friday, at(next_friday - timedelta(days=2), 12), 90),
        ]
    )
    assert baseline_forecast(with_late_rush, next_friday, now) == baseline_forecast(early, next_friday, now)


def test_it_never_looks_at_the_evening_itself_or_anything_after_the_run():
    """A backtest must not peek. Changing the day's own guests, or a later day's, changes nothing."""
    target = FRIDAY                              # a Friday that is in the history
    now = at(FRIDAY - timedelta(days=6))         # forecast made a week before, 7 days ahead
    history = fridays_history()
    peeking = fridays_history()
    peeking._guests[FRIDAY] = 999
    forecast = baseline_forecast(history, target, now)
    assert baseline_forecast(peeking, target, now) == forecast
    assert FRIDAY not in forecast.reference_days and max(forecast.reference_days) == FRIDAY - timedelta(days=7)
    assert forecast.guests == 100


def test_a_week_in_the_future_is_skipped_as_reference():
    history = fridays_history()
    in_two_weeks = FRIDAY + timedelta(days=14)
    references = reference_days(history, in_two_weeks, FRIDAY + timedelta(days=1))
    assert references[0] == FRIDAY and len(references) == 6


def test_refuses_to_guess_without_enough_history():
    two_fridays = History(TZ, {FRIDAY: 100, FRIDAY - timedelta(days=7): 100}, [])
    with pytest.raises(ForecastError, match="only 2 earlier Friday"):
        baseline_forecast(two_fridays, FRIDAY + timedelta(days=7), at(FRIDAY + timedelta(days=1)))


def test_refuses_an_evening_that_is_already_over():
    with pytest.raises(ForecastError, match="already over"):
        baseline_forecast(fridays_history(), FRIDAY, at(FRIDAY + timedelta(days=1)))
