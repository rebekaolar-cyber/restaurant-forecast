"""Loads daily weather for every restaurant from Open-Meteo into the daily_weather table.

    python -m forecast.weather                       two years of history plus the 14-day forecast
    python -m forecast.weather --history-days 30     a shorter look back
    python -m forecast.weather --expect-unchanged    also fail if this run added rows

Running it again is always safe: a day that is already in the table is updated, never added a
second time. Yesterday's forecast row becomes a measured row once the day has passed.

Needs SUPABASE_URL and SUPABASE_SECRET_KEY in the environment.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from forecast import report
from forecast.db import Database, DatabaseError, RestDatabase
from forecast.settings import SettingsError, load_settings

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"   # measured weather
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"         # forecast, plus the last few days

FORECAST_DAYS = 14          # today and the 13 days after it
RECENT_DAYS = 10            # the forecast service is also asked for the last 10 days, in case
                            # the archive does not have the most recent days yet
DEFAULT_HISTORY_DAYS = 731  # two years

ATTEMPTS = 3
TIMEOUT_SECONDS = 30

# Open-Meteo's name -> (our column, the unit we expect, lowest and highest value we believe)
FIELDS = {
    "temperature_2m_max": ("temp_max", "°C", -50.0, 60.0),
    "precipitation_sum": ("rain_mm", "mm", 0.0, 500.0),
    "wind_speed_10m_max": ("wind_max", "km/h", 0.0, 300.0),
    "sunshine_duration": ("sunshine_hours", "s", 0.0, 24.0),
}
# A day without these two is treated as "no weather for that day".
REQUIRED = ("temp_max", "rain_mm")


class WeatherError(RuntimeError):
    """The weather service gave an answer we cannot trust, or the table does not look right."""


@dataclass(frozen=True)
class LoadSummary:
    restaurant: str
    first_day: date
    last_day: date
    measured_days: int
    forecast_days: int
    rows_before: int
    rows_after: int

    def text(self) -> str:
        return (
            f"{self.measured_days + self.forecast_days} days written, {self.first_day} to {self.last_day} "
            f"({self.measured_days} measured, {self.forecast_days} forecast). "
            f"Rows in the table: {self.rows_before} before, {self.rows_after} after."
        )


def fetch_json(
    session: requests.Session, url: str, params: dict, sleep: Callable[[float], None] = time.sleep
) -> dict:
    """Asks Open-Meteo and returns its answer. Tries again when the service is busy or unreachable."""
    problem = "no attempt was made"
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as error:
            problem = f"could not reach the weather service ({type(error).__name__})"
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    problem = "the weather service answered with something that is not JSON"
            else:
                try:
                    reason = response.json().get("reason", "no reason given")
                except (ValueError, AttributeError):
                    reason = "no reason given"
                problem = f"the weather service answered HTTP {response.status_code}: {reason}"
                if response.status_code < 500 and response.status_code != 429:
                    break  # the question itself is wrong: asking again will not help
        if attempt < ATTEMPTS:
            sleep(2 * attempt)
    raise WeatherError(problem)


def parse_daily(payload: dict) -> dict[date, dict]:
    """Turns one Open-Meteo answer into {day: {our column: value}}.

    Checks the units and the values on the way, so a silent change at Open-Meteo (say, wind in
    mph) stops the job instead of quietly filling the table with wrong numbers.
    """
    try:
        daily, units = payload["daily"], payload["daily_units"]
        times = daily["time"]
    except (KeyError, TypeError):
        raise WeatherError("the weather answer has no daily values") from None

    days: dict[date, dict] = {date.fromisoformat(text): {} for text in times}
    if len(days) != len(times):
        raise WeatherError("the weather answer lists the same day twice")

    for source, (column, unit, lowest, highest) in FIELDS.items():
        if units.get(source) != unit:
            raise WeatherError(f"{source} is in {units.get(source)!r}, expected {unit!r}")
        values = daily.get(source)
        if not isinstance(values, list) or len(values) != len(times):
            raise WeatherError(f"{source} does not have one value per day")
        for day, value in zip(days, values):
            if value is not None:
                value = float(value) / 3600 if column == "sunshine_hours" else float(value)
                value = round(value, 1)
                if not lowest <= value <= highest:
                    raise WeatherError(f"{column} on {day} is {value}, which cannot be right")
            days[day][column] = value
    return days


def _usable(values: dict | None) -> bool:
    return values is not None and all(values.get(column) is not None for column in REQUIRED)


def build_rows(
    restaurant_id: str, today: date, first_day: date, archive: dict[date, dict], recent: dict[date, dict]
) -> list[dict]:
    """One row per day from first_day up to 13 days after today.

    Past days take the measured value from the archive; if the archive does not have a day yet,
    the forecast service's value for that day is used. Today and later are forecasts.
    """
    last_day = today + timedelta(days=FORECAST_DAYS - 1)
    rows, missing = [], []
    day = first_day
    while day <= last_day:
        is_forecast = day >= today
        values = None if is_forecast else archive.get(day)
        if not _usable(values):
            values = recent.get(day)
        if _usable(values):
            rows.append({"restaurant_id": restaurant_id, "date": day.isoformat(), **values, "is_forecast": is_forecast})
        else:
            missing.append(day)
        day += timedelta(days=1)

    if missing:
        shown = ", ".join(d.isoformat() for d in missing[:5]) + (" ..." if len(missing) > 5 else "")
        raise WeatherError(f"no weather for {len(missing)} day(s): {shown}")
    return rows


def load_restaurant(
    db: Database,
    session: requests.Session,
    restaurant: dict,
    *,
    today: date | None = None,
    history_days: int = DEFAULT_HISTORY_DAYS,
    sleep: Callable[[float], None] = time.sleep,
) -> LoadSummary:
    """Fetches, checks and writes the weather for one restaurant, then reads the table back."""
    if history_days < 1:
        raise WeatherError("history-days must be at least 1")
    restaurant_id = restaurant["id"]
    today = today or datetime.now(ZoneInfo(restaurant["timezone"])).date()
    first_day = today - timedelta(days=history_days)
    last_day = today + timedelta(days=FORECAST_DAYS - 1)

    place = {
        "latitude": restaurant["latitude"],
        "longitude": restaurant["longitude"],
        "timezone": restaurant["timezone"],  # so that a "day" is a day at the restaurant
        "daily": ",".join(FIELDS),
    }
    archive = parse_daily(
        fetch_json(
            session,
            ARCHIVE_URL,
            {**place, "start_date": first_day.isoformat(), "end_date": (today - timedelta(days=1)).isoformat()},
            sleep,
        )
    )
    recent = parse_daily(
        fetch_json(session, FORECAST_URL, {**place, "past_days": RECENT_DAYS, "forecast_days": FORECAST_DAYS}, sleep)
    )
    rows = build_rows(restaurant_id, today, first_day, archive, recent)

    mine = [("restaurant_id", "eq", restaurant_id)]
    rows_before = db.count("daily_weather", mine)
    db.upsert("daily_weather", rows, on_conflict=["restaurant_id", "date"])
    rows_after = db.count("daily_weather", mine)

    # Read the table back instead of trusting the write.
    window = mine + [("date", "gte", first_day), ("date", "lte", last_day)]
    in_table = db.count("daily_weather", window)
    if in_table != len(rows):
        raise WeatherError(f"wrote {len(rows)} days but the table holds {in_table} for the same period")
    upcoming = db.count("daily_weather", window + [("date", "gte", today), ("is_forecast", "eq", True)])
    if upcoming != FORECAST_DAYS:
        raise WeatherError(f"expected {FORECAST_DAYS} forecast days from {today}, the table holds {upcoming}")
    stale = db.count("daily_weather", mine + [("date", "lt", today), ("is_forecast", "eq", True)])
    if stale:
        raise WeatherError(
            f"{stale} past day(s) are still marked as forecast. Run again with a larger --history-days to replace them."
        )

    return LoadSummary(
        restaurant=restaurant["name"],
        first_day=first_day,
        last_day=last_day,
        measured_days=sum(not row["is_forecast"] for row in rows),
        forecast_days=sum(row["is_forecast"] for row in rows),
        rows_before=rows_before,
        rows_after=rows_after,
    )


def load_all(
    db: Database,
    session: requests.Session,
    *,
    today: date | None = None,
    history_days: int = DEFAULT_HISTORY_DAYS,
    expect_unchanged: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> list[LoadSummary]:
    restaurants = db.select("restaurants", "id,name,latitude,longitude,timezone", order="name")
    if not restaurants:
        raise WeatherError("there is no restaurant in the database")

    summaries = []
    for restaurant in restaurants:
        summary = load_restaurant(db, session, restaurant, today=today, history_days=history_days, sleep=sleep)
        if expect_unchanged and summary.rows_after != summary.rows_before:
            raise WeatherError(
                f"this run added {summary.rows_after - summary.rows_before} row(s) for {summary.restaurant}; "
                "a repeat run must add none"
            )
        summaries.append(summary)
    return summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load daily weather from Open-Meteo into daily_weather.")
    parser.add_argument("--history-days", type=int, default=DEFAULT_HISTORY_DAYS, help="how many days back to load")
    parser.add_argument("--expect-unchanged", action="store_true", help="fail if this run adds rows")
    args = parser.parse_args(argv)
    title = "Weather, repeat run" if args.expect_unchanged else "Weather"

    try:
        settings = load_settings()
        db = RestDatabase(settings.supabase_url, settings.supabase_secret_key)
        summaries = load_all(
            db, requests.Session(), history_days=args.history_days, expect_unchanged=args.expect_unchanged
        )
    except (SettingsError, WeatherError, DatabaseError) as error:
        report.failure(title, str(error))
        return 1

    for summary in summaries:
        report.result(f"{title}: {summary.restaurant}", summary.text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
