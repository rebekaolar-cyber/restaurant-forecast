"""The baseline forecast: simple enough to check by hand.

For one evening:

1. Take the guests on the same weekday over the last 6 weeks and average them.
2. Look at the reservation book. Count the guests already booked for the evening, and compare
   that with what was booked for those 6 earlier evenings at the same distance from the day.
3. If 20 more guests than usual are already booked, the forecast goes up by 20. If 20 fewer,
   it goes down by 20. The correction is kept within half of the average either way.

"Days ahead" is counted the way the nightly job writes it: day 1 is the evening of the day the
job runs (it runs in the night), day 14 is thirteen days later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from forecast.history import History

MODEL_NAME = "baseline"
WEEKS = 6          # how many earlier evenings of the same weekday are averaged
MIN_WEEKS = 3      # with fewer than this the forecast refuses to guess
MAX_CORRECTION = 0.5   # the bookings can move the forecast by at most half the average


class ForecastError(RuntimeError):
    """There is not enough history to make a forecast."""


@dataclass(frozen=True)
class Forecast:
    day: date
    days_ahead: int
    guests: int                  # the forecast
    weekday_average: float       # step 1 on its own
    booked_now: int              # guests in the book for this evening at the moment of forecasting
    booked_normally: float       # the same for the earlier evenings, at the same distance
    reference_days: tuple[date, ...]


def reference_days(history: History, day: date, run_day: date) -> list[date]:
    """The most recent evenings of the same weekday that were over when the forecast was made."""
    found: list[date] = []
    candidate = day - timedelta(days=7)
    oldest_worth_trying = run_day - timedelta(days=7 * (WEEKS + 8))
    while len(found) < WEEKS and candidate >= oldest_worth_trying:
        if candidate < run_day and history.guests(candidate) is not None:
            found.append(candidate)
        candidate -= timedelta(days=7)
    return found


def baseline_forecast(history: History, day: date, as_of: datetime) -> Forecast:
    """The forecast for one evening, using only what was known at the moment `as_of`."""
    local_now = as_of.astimezone(history.tz)
    run_day = local_now.date()
    if day < run_day:
        raise ForecastError(f"{day} is already over at {local_now:%Y-%m-%d %H:%M}")

    references = reference_days(history, day, run_day)
    if len(references) < MIN_WEEKS:
        raise ForecastError(
            f"only {len(references)} earlier {day:%A}(s) with receipts before {run_day}; at least {MIN_WEEKS} are needed"
        )
    weekday_average = sum(history.guests(ref) for ref in references) / len(references)

    booked_now = history.booked(day, as_of)
    # For each earlier evening: what was in the book at the same clock time, the same number of
    # days before it.
    booked_normally = sum(history.booked(ref, local_now - (day - ref)) for ref in references) / len(references)

    correction = booked_now - booked_normally
    limit = MAX_CORRECTION * weekday_average
    correction = max(-limit, min(limit, correction))
    return Forecast(
        day=day,
        days_ahead=(day - run_day).days + 1,
        guests=max(0, round(weekday_average + correction)),
        weekday_average=weekday_average,
        booked_now=booked_now,
        booked_normally=booked_normally,
        reference_days=tuple(references),
    )
