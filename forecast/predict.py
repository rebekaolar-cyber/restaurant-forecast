"""Writes the forecast for the next 14 evenings into the forecasts table.

    python -m forecast.predict

For each evening: guests from the baseline forecast, then staff per role from the manager's
table. One row per restaurant, date and shift; a row that is already there is replaced.
It never touches forecast_overrides, and it has no right to.

Needs SUPABASE_URL and SUPABASE_SECRET_KEY in the environment.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from forecast import report
from forecast.baseline import MODEL_NAME, WEEKS, Forecast, ForecastError, baseline_forecast
from forecast.db import Database, DatabaseError, RestDatabase
from forecast.history import History, load_history
from forecast.settings import SettingsError, load_settings
from forecast.staffing import ROLES, StaffingError, load_bands, roster_text, staff_for

HORIZON_DAYS = 14   # today and the 13 days after it
SHIFT = "dinner"    # the restaurant is open for dinner only


@dataclass(frozen=True)
class PredictSummary:
    restaurant: str
    first_day: date
    last_day: date
    guests: tuple[int, ...]
    tonight: str

    def text(self) -> str:
        return (
            f"14 evenings written, {self.first_day} to {self.last_day}. "
            f"Guests per evening: {', '.join(str(g) for g in self.guests)}. "
            f"Tonight: {self.guests[0]} guests, {self.tonight}."
        )


def forecast_rows(history: History, bands: list[dict], restaurant_id: str, as_of: datetime) -> list[dict]:
    """The 14 rows for the forecasts table, as of the moment `as_of`."""
    today = as_of.astimezone(history.tz).date()
    made_at = as_of.astimezone(timezone.utc).isoformat()
    rows = []
    for offset in range(HORIZON_DAYS):
        forecast: Forecast = baseline_forecast(history, today + timedelta(days=offset), as_of)
        rows.append(
            {
                "restaurant_id": restaurant_id,
                "date": forecast.day.isoformat(),
                "shift": SHIFT,
                "predicted_guests": forecast.guests,
                **staff_for(forecast.guests, bands),
                "model": MODEL_NAME,
                "created_at": made_at,
            }
        )
    return rows


def predict(db: Database, restaurant: dict, *, as_of: datetime) -> PredictSummary:
    """Makes and writes the forecast for one restaurant, then reads the table back."""
    tz = ZoneInfo(restaurant["timezone"])
    today = as_of.astimezone(tz).date()
    last_day = today + timedelta(days=HORIZON_DAYS - 1)
    mine = [("restaurant_id", "eq", restaurant["id"])]

    bands = load_bands(db, restaurant["id"])
    # Far enough back for 6 same-weekday evenings before today, with some room for gaps.
    history = load_history(db, restaurant, first_day=today - timedelta(days=7 * (WEEKS + 4)), last_day=last_day)
    rows = forecast_rows(history, bands, restaurant["id"], as_of)

    overrides_before = db.count("forecast_overrides", mine)
    db.upsert("forecasts", rows, on_conflict=["restaurant_id", "date", "shift"])

    # Read the table back instead of trusting the write.
    window = mine + [("date", "gte", today), ("date", "lte", last_day), ("shift", "eq", SHIFT)]
    stored = db.select("forecasts", "date,predicted_guests,model," + ",".join(ROLES), window, order="date")
    if [row["date"] for row in stored] != [row["date"] for row in rows]:
        raise ForecastError(f"wrote {len(rows)} evenings but the table holds {len(stored)} for the same period")
    for written, row in zip(rows, stored):
        if row["model"] != MODEL_NAME or any(row[column] != written[column] for column in ("predicted_guests", *ROLES)):
            raise ForecastError(f"the forecast for {row['date']} in the table is not the one just written")
    if db.count("forecast_overrides", mine) != overrides_before:
        # The job cannot write overrides, so this can only be the manager saving one right now.
        report.say("An override was added or removed while the job ran. That was not this job.")

    return PredictSummary(
        restaurant=restaurant["name"],
        first_day=today,
        last_day=last_day,
        guests=tuple(row["predicted_guests"] for row in rows),
        tonight=roster_text(rows[0]),
    )


def predict_all(db: Database, *, as_of: datetime) -> list[PredictSummary]:
    restaurants = db.select("restaurants", "id,name,timezone", order="name")
    if not restaurants:
        raise ForecastError("there is no restaurant in the database")
    return [predict(db, restaurant, as_of=as_of) for restaurant in restaurants]


def main(argv: list[str] | None = None) -> int:
    try:
        settings = load_settings()
        db = RestDatabase(settings.supabase_url, settings.supabase_secret_key)
        summaries = predict_all(db, as_of=datetime.now(timezone.utc).replace(microsecond=0))
    except (SettingsError, ForecastError, StaffingError, DatabaseError) as error:
        report.failure("Forecast", str(error))
        return 1
    for summary in summaries:
        report.result(f"Forecast: {summary.restaurant}", summary.text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
