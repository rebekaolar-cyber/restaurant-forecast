"""How good is the forecast? Replays the last 3 months and compares with what really happened.

For every evening in the period and for 1, 3, 7 and 14 days ahead, it makes the forecast using
only what was known at that moment, and measures how far off it was. Next to our forecast it
always shows the benchmark: the manager's own weekly plan (the same guests per weekday, every
week). Our forecast has to beat it.

    python -m forecast.backtest                         from the database
    python -m forecast.backtest --offline forecast/tests/samples/daily_weather_2024-10-09_to_2026-10-23.csv \\
        --as-of 2026-10-10T03:00:00+02:00 --report-dir forecast/reports
                                                        without a database: rebuilds the fake
                                                        history from saved weather, writes the report

"Days ahead" is counted the way the nightly job writes the forecast: day 1 is the evening of the
day the job runs (it runs in the night before), day 14 is thirteen days later.

All of this runs on fake history. It shows that the method works on data shaped like the
restaurant's. It cannot show how good the forecast is on the restaurant's real evenings.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from forecast import fake_history, report
from forecast.baseline import WEEKS, ForecastError, baseline_forecast
from forecast.db import Database, DatabaseError, RestDatabase
from forecast.history import History, load_history, local_moment
from forecast.opening import is_open
from forecast.manager_plan import GUESTS_BY_WEEKDAY, REAL_FRIDAY_GUESTS, planned_guests
from forecast.settings import SettingsError, load_settings
from forecast.staffing import StaffingError, load_bands, staff_for

HORIZONS = (1, 3, 7, 14)   # days ahead
DAYS = 92                  # the last 3 months
RUN_AT = time(3, 0)        # the nightly job runs around 03:00 in Amsterdam
PLAN_SCALE = REAL_FRIDAY_GUESTS / GUESTS_BY_WEEKDAY[4]   # 174 real guests against 250 planned
FLOOR_ROLES = ("servers", "bar_staff", "runners", "food_staff")   # the roster; kitchen is fixed
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# The seeded test restaurant and its staffing table, for running without a database.
# Must stay equal to supabase/seed.sql; a test checks that.
OFFLINE_RESTAURANT = {
    "id": "35f0d253-0e43-4e2f-8c23-d52b4ca159f7",
    "name": "Restaurant Habibi",
    "timezone": "Europe/Amsterdam",
    "seats": 254,
}
OFFLINE_BANDS = [
    {"guests_from": 100, "servers": 3, "bar_staff": 1, "runners": 1, "food_staff": 2, "cooks": 4},
    {"guests_from": 120, "servers": 4, "bar_staff": 2, "runners": 2, "food_staff": 3, "cooks": 4},
    {"guests_from": 180, "servers": 6, "bar_staff": 3, "runners": 2, "food_staff": 3, "cooks": 4},
    {"guests_from": 250, "servers": 6, "bar_staff": 3, "runners": 3, "food_staff": 4, "cooks": 4},
    {"guests_from": 300, "servers": 6, "bar_staff": 3, "runners": 3, "food_staff": 4, "cooks": 4},
]


def _score(errors: list[float]) -> dict:
    """Average size of the miss, and whether it leans high (+) or low (-)."""
    return {
        "average_error": round(sum(abs(e) for e in errors) / len(errors), 1),
        "leaning": round(sum(errors) / len(errors), 1),
    }


def _floor_staff(guests: int, bands: list[dict]) -> int:
    staff = staff_for(guests, bands)
    return sum(staff[role] for role in FLOOR_ROLES)


def run_backtest(history: History, bands: list[dict], *, last_day: date, days: int = DAYS) -> dict:
    """Replays `days` evenings ending on last_day. Returns plain numbers, ready to save as JSON."""
    period = [last_day - timedelta(days=n) for n in range(days - 1, -1, -1)]
    closed = [day for day in period if not is_open(day)]
    missing = [day for day in period if is_open(day) and history.guests(day) is None]
    if missing:
        raise ForecastError(f"no receipts for {len(missing)} evening(s) in the period, first {missing[0]}")

    # An evening is scored only if a forecast could be made at every distance. A weekday that has
    # only just opened (Mondays from 10 August 2026) has too few earlier weeks at first.
    def forecastable(day: date) -> bool:
        try:
            for days_ahead in HORIZONS:
                baseline_forecast(history, day, local_moment(day - timedelta(days=days_ahead - 1), RUN_AT, history.tz))
        except ForecastError:
            return False
        return True

    open_evenings = [day for day in period if is_open(day)]
    evenings = [day for day in open_evenings if forecastable(day)]
    too_new = [day for day in open_evenings if day not in evenings]
    if not evenings:
        raise ForecastError("no evening in the period could be forecast")

    horizons = {}
    for days_ahead in HORIZONS:
        errors = {"forecast": [], "weekday_average": [], "manager_plan": [], "manager_plan_scaled": []}
        closer = 0
        staff = {"forecast_right": 0, "plan_right": 0, "forecast_extra": 0, "forecast_short": 0, "plan_extra": 0, "plan_short": 0}
        for day in evenings:
            actual = history.guests(day)
            as_of = local_moment(day - timedelta(days=days_ahead - 1), RUN_AT, history.tz)
            forecast = baseline_forecast(history, day, as_of)
            plan = planned_guests(day)
            errors["forecast"].append(forecast.guests - actual)
            errors["weekday_average"].append(round(forecast.weekday_average) - actual)
            errors["manager_plan"].append(plan - actual)
            errors["manager_plan_scaled"].append(round(plan * PLAN_SCALE) - actual)
            closer += abs(forecast.guests - actual) < abs(plan - actual)

            needed = _floor_staff(actual, bands)
            for name, guests in (("forecast", forecast.guests), ("plan", plan)):
                rostered = _floor_staff(guests, bands)
                staff[f"{name}_right"] += rostered == needed
                staff[f"{name}_extra"] += max(0, rostered - needed)
                staff[f"{name}_short"] += max(0, needed - rostered)
        horizons[str(days_ahead)] = {
            **{name: _score(values) for name, values in errors.items()},
            "evenings_forecast_closer_than_plan": closer,
            "staffing": staff,
        }

    by_weekday = {}
    for weekday, name in enumerate(WEEKDAYS):
        own = [day for day in evenings if day.weekday() == weekday]
        if own:
            by_weekday[name] = {
                "evenings": len(own),
                "average_guests": round(sum(history.guests(day) for day in own) / len(own), 1),
                "manager_plan": GUESTS_BY_WEEKDAY[weekday],
            }

    return {
        "first_evening": period[0].isoformat(),
        "last_evening": period[-1].isoformat(),
        "evenings": len(evenings),
        "evenings_closed": len(closed),
        "evenings_too_new": len(too_new),
        "average_guests": round(sum(history.guests(day) for day in evenings) / len(evenings), 1),
        "horizons": horizons,
        "by_weekday": by_weekday,
    }


def beats_the_plan(result: dict) -> bool:
    """True if our forecast misses by less than the manager's plan at every distance."""
    return all(
        scores["forecast"]["average_error"] < scores["manager_plan"]["average_error"]
        for scores in result["horizons"].values()
    )


def summary_lines(result: dict) -> list[str]:
    lines = []
    for days_ahead, scores in result["horizons"].items():
        lines.append(
            f"{days_ahead} day(s) ahead: forecast off by {scores['forecast']['average_error']} guests on average, "
            f"manager's plan by {scores['manager_plan']['average_error']}, "
            f"plan scaled to the real Friday by {scores['manager_plan_scaled']['average_error']}, "
            f"weekday average alone by {scores['weekday_average']['average_error']}"
        )
    return lines


def markdown_report(result: dict, *, source: str) -> str:
    """The report as a page of text for forecast/reports/."""
    n = result["evenings"]
    out = [
        "# Baseline forecast: backtest against the manager's plan",
        "",
        f"Period: {result['first_evening']} to {result['last_evening']}, {n} evenings scored, dinner shift. "
        f"Average {result['average_guests']} guests per evening.",
        "",
        f"Not scored: {result['evenings_closed']} evening(s) when the restaurant was closed (Mondays before "
        f"10 August 2026) and {result['evenings_too_new']} Monday(s) right after it opened, when there were "
        "not yet 3 earlier Mondays to average.",
        "",
        f"Data: {source}",
        "",
        "**This is fake history.** It shows the method works on data shaped like the restaurant's. "
        "It does not show how good the forecast is on the restaurant's real evenings.",
        "",
        "## Average error in guests per evening",
        "",
        "Lower is better. \"Days ahead\" counts as the nightly job writes it: day 1 is the evening of the "
        "day the job runs, day 14 is thirteen days later.",
        "",
        "| Days ahead | Our forecast | Weekday average alone | Manager's plan | Manager's plan x 0.70 |",
        "|---|---|---|---|---|",
    ]
    for days_ahead, scores in result["horizons"].items():
        out.append(
            f"| {days_ahead} | {scores['forecast']['average_error']} | {scores['weekday_average']['average_error']} "
            f"| {scores['manager_plan']['average_error']} | {scores['manager_plan_scaled']['average_error']} |"
        )
    out += [
        "",
        "- **Our forecast**: the average of the same weekday over the last 6 weeks, corrected by how the "
        "bookings already made compare with what is normal that many days ahead.",
        "- **Weekday average alone**: the same without looking at the bookings. The difference between "
        "these two columns is what the reservation book adds.",
        "- **Manager's plan**: Mon 100, Tue 100, Wed 100, Thu 120, Fri 250, Sat 300, Sun 180, every week.",
        f"- **Manager's plan x 0.70**: his plan scaled by 174/250, the one real Friday we know "
        "(47 reservations, 174 people against 250 planned). In this fake history that is exactly the "
        "level the evenings were built around, so it is the best any fixed weekly plan could do here. "
        "Nobody has that number for the real restaurant.",
        "",
        "Verdict: " + (
            "our forecast beats the manager's plan at every distance."
            if beats_the_plan(result)
            else "our forecast does NOT beat the manager's plan at every distance."
        ),
        "",
        "## Why the plan is so far off here",
        "",
        "The fake history was built about 30% below his plan on every weekday, because the one real "
        "number we have says so for a Friday. That is an assumption for the other six days. Most of "
        "the plan's error in the table above comes from this level difference, not from anything clever "
        "in the forecast. Compare our forecast with the last column to see what it adds beyond the level.",
        "",
        "| Weekday | Evenings | Average guests (fake) | Manager's plan |",
        "|---|---|---|---|",
    ]
    for name, row in result["by_weekday"].items():
        out.append(f"| {name} | {row['evenings']} | {row['average_guests']} | {row['manager_plan']} |")
    earlier = result.get("earlier_period")
    if earlier:
        out += [
            "",
            "## A longer look: the months before",
            "",
            f"The same comparison for {earlier['first_evening']} to {earlier['last_evening']} "
            f"({earlier['evenings']} evenings, average {earlier['average_guests']} guests). Three summer months "
            "are a small sample without a single public holiday. This longer period has Christmas, Easter "
            "and the quiet January weeks in it, which is where the reservation book earns its place.",
            "",
            "| Days ahead | Our forecast | Weekday average alone | Manager's plan | Manager's plan x 0.70 |",
            "|---|---|---|---|---|",
        ]
        for days_ahead, scores in earlier["horizons"].items():
            out.append(
                f"| {days_ahead} | {scores['forecast']['average_error']} | {scores['weekday_average']['average_error']} "
                f"| {scores['manager_plan']['average_error']} | {scores['manager_plan_scaled']['average_error']} |"
            )
    out += [
        "",
        "## What it means for the roster",
        "",
        "Floor, bar, runner and food staff together, from the manager's own table, for the forecast made "
        "7 days ahead. \"Right roster\" means the same table row as the real guest number called for. "
        "This depends on how the table is read between its rows (a row applies from its guest number "
        "up to the next row), which the manager still has to confirm.",
        "",
        "| | Our forecast | Manager's plan |",
        "|---|---|---|",
    ]
    staff = result["horizons"]["7"]["staffing"]
    out += [
        f"| Evenings with the right roster | {staff['forecast_right']} of {n} | {staff['plan_right']} of {n} |",
        f"| Staff rostered beyond what was needed (person-evenings) | {staff['forecast_extra']} | {staff['plan_extra']} |",
        f"| Staff short of what was needed (person-evenings) | {staff['forecast_short']} | {staff['plan_short']} |",
        "",
    ]
    return "\n".join(out)


# ---- where the history comes from -------------------------------------------------------------


def offline_history(weather_csv: Path, as_of: datetime) -> History:
    """Rebuilds the fake history in memory from a saved weather file. Needs no database."""
    weather = {}
    with weather_csv.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["is_forecast"] == "false":
                weather[date.fromisoformat(row["date"])] = row
    bookings, receipts = fake_history.generate(OFFLINE_RESTAURANT, weather, first_day=min(weather), as_of=as_of)
    return History.from_rows(ZoneInfo(OFFLINE_RESTAURANT["timezone"]), bookings, receipts)


def database_history(db: Database, restaurant: dict, last_day: date) -> History:
    # Far enough back for the first evening's forecast 14 days ahead to find its 6 earlier weeks.
    first_day = last_day - timedelta(days=DAYS + HORIZONS[-1] + 7 * (WEEKS + 4))
    return load_history(db, restaurant, first_day=first_day, last_day=last_day)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest the forecast against the manager's plan.")
    parser.add_argument("--offline", type=Path, metavar="WEATHER_CSV", help="rebuild the fake history from this file instead of reading the database")
    parser.add_argument("--as-of", help="pretend it is this moment, for example 2026-10-10T03:00:00+02:00")
    parser.add_argument("--report-dir", type=Path, help="also write baseline_backtest.md and .json here")
    args = parser.parse_args(argv)

    try:
        as_of = fake_history.parse_as_of(args.as_of)
        if args.offline:
            tz = ZoneInfo(OFFLINE_RESTAURANT["timezone"])
            last_day = as_of.astimezone(tz).date() - timedelta(days=1)
            history = offline_history(args.offline, as_of)
            result = run_backtest(history, OFFLINE_BANDS, last_day=last_day)
            # Everything before the 3 months, leaving the first weeks as run-up for the averages.
            earliest = history.days_with_guests()[0] + timedelta(days=7 * (WEEKS + 2))
            before = date.fromisoformat(result["first_evening"]) - timedelta(days=1)
            if before > earliest:
                earlier = run_backtest(history, OFFLINE_BANDS, last_day=before, days=(before - earliest).days + 1)
                result["earlier_period"] = {key: earlier[key] for key in ("first_evening", "last_evening", "evenings", "average_guests", "horizons")}
            source = (
                f"fake history rebuilt from the saved weather file `{args.offline.name}` with seed {fake_history.SEED}, "
                f"as of {as_of.astimezone(tz):%Y-%m-%d %H:%M} Amsterdam time."
            )
        else:
            settings = load_settings()
            db = RestDatabase(settings.supabase_url, settings.supabase_secret_key)
            restaurants = db.select("restaurants", "id,name,timezone", order="name")
            if len(restaurants) != 1:
                raise ForecastError(f"the backtest expects exactly one restaurant, found {len(restaurants)}")
            restaurant = restaurants[0]
            last_day = as_of.astimezone(ZoneInfo(restaurant["timezone"])).date() - timedelta(days=1)
            history = database_history(db, restaurant, last_day)
            result = run_backtest(history, load_bands(db, restaurant["id"]), last_day=last_day)
            source = "bookings and receipts in the database."
    except (SettingsError, ForecastError, StaffingError, fake_history.FakeHistoryError, DatabaseError) as error:
        report.failure("Backtest", str(error))
        return 1

    title = f"Backtest {result['first_evening']} to {result['last_evening']}"
    for line in summary_lines(result):
        report.result(title, line)
    verdict = "beats" if beats_the_plan(result) else "does NOT beat"
    report.result(title, f"our forecast {verdict} the manager's plan at every distance (fake history)")

    if args.report_dir:
        args.report_dir.mkdir(parents=True, exist_ok=True)
        (args.report_dir / "baseline_backtest.md").write_text(markdown_report(result, source=source), encoding="utf-8")
        (args.report_dir / "baseline_backtest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        report.say(f"Report written to {args.report_dir.as_posix()}/baseline_backtest.md and .json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
