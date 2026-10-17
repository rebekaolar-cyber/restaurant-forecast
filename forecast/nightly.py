"""The nightly job: weather, then the forecast, then write it. One command, in that order.

    python -m forecast.nightly --fake-feed

1. Weather: the last 30 days again (measured values replace yesterday's forecast) and the next 14.
2. Fake bookings (only with --fake-feed): brings the made-up reservation book and till up to
   now, so there is a "yesterday" to learn from. Remove this step when real bookings are imported.
3. Forecast: guests for the next 14 evenings, staff per role from the manager's table, written to
   the forecasts table.

If any step fails, the job stops there and exits with an error, so GitHub marks the run as failed
and sends an email. It never writes forecast_overrides: it has no right to, and no code for it.

    --as-of 2026-10-10T03:00:00+02:00   pretend it is this moment (for tests and repeat runs)
    --expect-unchanged                  also fail if this run added rows (a repeat run must not)

Needs SUPABASE_URL and SUPABASE_SECRET_KEY in the environment.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from forecast import fake_history, predict, report, weather
from forecast.baseline import ForecastError
from forecast.db import Database, DatabaseError, RestDatabase
from forecast.settings import SettingsError, load_settings
from forecast.staffing import StaffingError

WEATHER_HISTORY_DAYS = 30

EXPECTED_ERRORS = (
    SettingsError,
    weather.WeatherError,
    fake_history.FakeHistoryError,
    ForecastError,
    StaffingError,
    DatabaseError,
)


class NightlyError(RuntimeError):
    """A step of the nightly job failed. The message names the step."""


def run(
    db: Database,
    session: requests.Session,
    *,
    as_of: datetime,
    fake_feed: bool,
    expect_unchanged: bool = False,
    sleep=None,
) -> None:
    """Runs the steps in order. Raises NightlyError naming the step that failed."""
    step = "Weather"
    try:
        options = {} if sleep is None else {"sleep": sleep}
        restaurants = db.select("restaurants", "id,name,latitude,longitude,timezone", order="name")
        if not restaurants:
            raise weather.WeatherError("there is no restaurant in the database")
        for restaurant in restaurants:
            today = as_of.astimezone(ZoneInfo(restaurant["timezone"])).date()
            summary = weather.load_restaurant(
                db, session, restaurant, today=today, history_days=WEATHER_HISTORY_DAYS, **options
            )
            if expect_unchanged and summary.rows_after != summary.rows_before:
                raise weather.WeatherError(f"this run added {summary.rows_after - summary.rows_before} weather row(s)")
            report.result(f"1 Weather: {summary.restaurant}", summary.text())

        if fake_feed:
            step = "Fake bookings"
            for summary in fake_history.top_up_all(db, as_of=as_of, expect_unchanged=expect_unchanged):
                report.result(f"2 Fake bookings: {summary.restaurant}", summary.text())

        step = "Forecast"
        forecasts_before = db.count("forecasts")
        for summary in predict.predict_all(db, as_of=as_of):
            report.result(f"3 Forecast: {summary.restaurant}", summary.text())
        added = db.count("forecasts") - forecasts_before
        if expect_unchanged and added:
            raise ForecastError(f"this run added {added} forecast row(s); a repeat run must add none")
    except EXPECTED_ERRORS as error:
        raise NightlyError(f"{step} failed: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The nightly job: weather, forecast, write.")
    parser.add_argument("--fake-feed", action="store_true", help="also bring the fake bookings and receipts up to now")
    parser.add_argument("--as-of", help="pretend it is this moment, for example 2026-10-10T03:00:00+02:00")
    parser.add_argument("--expect-unchanged", action="store_true", help="fail if this run adds rows")
    args = parser.parse_args(argv)
    title = "Nightly job, repeat run" if args.expect_unchanged else "Nightly job"

    try:
        as_of = fake_history.parse_as_of(args.as_of)
        settings = load_settings()
        db = RestDatabase(settings.supabase_url, settings.supabase_secret_key)
        run(db, requests.Session(), as_of=as_of, fake_feed=args.fake_feed, expect_unchanged=args.expect_unchanged)
    except (NightlyError, *EXPECTED_ERRORS) as error:
        report.failure(title, str(error))
        return 1
    except Exception as error:  # a bug: say so on the run page, then show the full trace in the log
        report.failure(title, f"unexpected {type(error).__name__}: {error}")
        raise

    report.result(title, f"finished without errors, as of {as_of.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
