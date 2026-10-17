"""Imports TheFork's "evolution of covers" export into the covers table.

    python -m forecast.import_covers FILE [FILE ...]            write to the database
    python -m forecast.import_covers FILE --period week          say the period size instead of
                                                                 letting the file tell it
    python -m forecast.import_covers FILE --sql > covers.sql     print SQL instead of writing

In TheFork, go to Reports > Evolution of covers, pick the period (day, week or month) and the
date range, and export as CSV. The file has exactly these columns:

    restaurantName,period,service,channel,offer,covers,bookings,no shows,cancellations,late cancellations

A file with any other header is refused. That is deliberate: TheFork's other exports carry guest
names and phone numbers, and those must never reach the database.

What the importer does with a row: `period` becomes period_start; period_end follows from the
period size (month: the last day of the month, week: the Sunday, day: the same day). The period
size is read from the file: all dates on the 1st means months, all Mondays a week apart means
weeks, anything else means days. `--period` overrides that. An offer of 0 means no offer and is
stored as ''. The restaurant is found by name (TheFork writes "Habibi" for "Restaurant Habibi").

Running the same file twice changes nothing: a row that is already there is updated, never
doubled. Every file is read and checked completely before anything is written; one bad value
and nothing is written at all. Later files win over earlier ones where they cover the same period.

Needs SUPABASE_URL and SUPABASE_SECRET_KEY in the environment, except with --sql.
"""

from __future__ import annotations

import argparse
import calendar
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from forecast import report
from forecast.db import Database, DatabaseError, RestDatabase
from forecast.import_tools import (
    ImportFileError,
    find_restaurant,
    load_restaurants,
    parse_count,
    parse_date,
    read_csv,
    sql_script,
    upsert_sql,
)
from forecast.settings import SettingsError, load_settings

TABLE = "covers"
SOURCE = "thefork"
HEADER = (
    "restaurantName", "period", "service", "channel", "offer",
    "covers", "bookings", "no shows", "cancellations", "late cancellations",
)
# File column -> table column, for the five numbers.
COUNTS = {
    "covers": "covers",
    "bookings": "bookings",
    "no shows": "no_shows",
    "cancellations": "cancellations",
    "late cancellations": "late_cancellations",
}
KEY = ("restaurant_id", "period_start", "period_end", "service", "channel", "offer")
PERIODS = ("day", "week", "month")


@dataclass(frozen=True)
class CoversFile:
    """One checked file, ready to be written."""

    restaurant: str            # the name as the file writes it
    period: str                # day, week or month
    rows: list[dict]           # table rows without restaurant_id, in file order

    @property
    def first_day(self) -> date:
        return min(row["period_start"] for row in self.rows)

    @property
    def last_day(self) -> date:
        return max(row["period_end"] for row in self.rows)


@dataclass(frozen=True)
class ImportSummary:
    rows_read: int
    rows_written: int
    period: str
    first_day: date
    last_day: date
    rows_before: int | None = None
    rows_after: int | None = None

    def text(self) -> str:
        text = f"{self.rows_read} rows read, {self.rows_written} rows written (per {self.period}, {self.first_day} to {self.last_day})."
        if self.rows_before is not None:
            text += f" Rows in the table: {self.rows_before} before, {self.rows_after} after."
        return text


def detect_period(days: list[date]) -> str:
    """Month if every date is the 1st; week if every date is a Monday and they lie whole weeks
    apart; otherwise day."""
    distinct = sorted(set(days))
    if all(day.day == 1 for day in distinct):
        return "month"
    if all(day.weekday() == 0 for day in distinct) and all(
        (later - earlier).days % 7 == 0 for earlier, later in zip(distinct, distinct[1:])
    ):
        return "week"
    return "day"


def period_end(start: date, period: str, where: str) -> date:
    if period == "month":
        if start.day != 1:
            raise ImportFileError(f"{where}: {start} is not the 1st of a month, but the period is month")
        return start.replace(day=calendar.monthrange(start.year, start.month)[1])
    if period == "week":
        if start.weekday() != 0:
            raise ImportFileError(f"{where}: {start} is not a Monday, but the period is week")
        return start + timedelta(days=6)
    if period == "day":
        return start
    raise ImportFileError(f"unknown period {period!r}, expected one of {', '.join(PERIODS)}")


def read_file(path: Path, period: str | None = None) -> CoversFile:
    """Reads and checks one export. Raises ImportFileError on the first problem."""
    raw = read_csv(path, HEADER)
    names = {row["restaurantName"] for row in raw}
    if len(names) != 1 or not next(iter(names)):
        raise ImportFileError(f"{path.name}: expected one restaurant name in every row, found {sorted(names)}")
    starts = [parse_date(row["period"], f"{path.name} line {n}") for n, row in enumerate(raw, start=2)]
    kind = period or detect_period(starts)

    rows = []
    for n, (row, start) in enumerate(zip(raw, starts), start=2):
        where = f"{path.name} line {n}"
        table_row = {
            "period_start": start,
            "period_end": period_end(start, kind, where),
            "service": row["service"],
            "channel": row["channel"],
            "offer": "" if row["offer"] == "0" else row["offer"],
        }
        if not table_row["channel"]:
            raise ImportFileError(f"{where}: the channel is empty")
        for column, target in COUNTS.items():
            table_row[target] = parse_count(row[column], f"{where}, {column}")
        table_row["source"] = SOURCE
        rows.append(table_row)

    repeated = [key for key, count in Counter(tuple(row[c] for c in KEY[1:]) for row in rows).items() if count > 1]
    if repeated:
        start, end, service, channel, offer = repeated[0]
        raise ImportFileError(
            f"{path.name}: the same period, service, channel and offer appears more than once "
            f"({start} to {end}, {service!r}, {channel!r}, {offer!r})"
        )
    return CoversFile(restaurant=next(iter(names)), period=kind, rows=rows)


def write_file(db: Database, checked: CoversFile, restaurants: list[dict]) -> ImportSummary:
    restaurant = find_restaurant(checked.restaurant, restaurants)
    mine = [("restaurant_id", "eq", restaurant["id"])]
    before = db.count(TABLE, mine)
    rows = [{"restaurant_id": restaurant["id"], **row, "period_start": row["period_start"].isoformat(),
             "period_end": row["period_end"].isoformat()} for row in checked.rows]
    db.upsert(TABLE, rows, on_conflict=KEY)
    return ImportSummary(
        rows_read=len(rows), rows_written=len(rows), period=checked.period,
        first_day=checked.first_day, last_day=checked.last_day,
        rows_before=before, rows_after=db.count(TABLE, mine),
    )


def import_files(db: Database, paths: list[Path], period: str | None = None) -> list[ImportSummary]:
    """Checks every file, then writes them in order. Nothing is written if any file is wrong."""
    files = [read_file(path, period) for path in paths]
    restaurants = load_restaurants(db)
    for checked in files:
        find_restaurant(checked.restaurant, restaurants)   # an unknown name stops everything
    return [write_file(db, checked, restaurants) for checked in files]


def sql_for_files(paths: list[Path], period: str | None = None) -> tuple[str, list[ImportSummary]]:
    """The SQL that would do the import, and the summaries. Nothing about the files but their
    contents goes into the SQL: no names, no paths."""
    files = [read_file(path, period) for path in paths]
    blocks, summaries = [], []
    for number, checked in enumerate(files, start=1):
        summary = ImportSummary(
            rows_read=len(checked.rows), rows_written=len(checked.rows), period=checked.period,
            first_day=checked.first_day, last_day=checked.last_day,
        )
        summaries.append(summary)
        blocks.append((f"covers, file {number} of {len(files)}: {summary.text()}", checked.restaurant,
                       upsert_sql(TABLE, checked.rows, KEY, checked.restaurant)))
    return sql_script(blocks), summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import TheFork's evolution-of-covers export into covers.")
    parser.add_argument("files", nargs="+", type=Path, metavar="FILE", help="CSV export(s) from TheFork")
    parser.add_argument("--period", choices=PERIODS, help="the period size, instead of reading it from the file")
    parser.add_argument("--sql", action="store_true", help="print SQL to stdout instead of writing to the database")
    args = parser.parse_args(argv)
    title = "Covers import"

    try:
        if args.sql:
            script, summaries = sql_for_files(args.files, args.period)
            sys.stdout.write(script)
            for path, summary in zip(args.files, summaries):
                print(f"{title}: {path.name}: {summary.text()}", file=sys.stderr)
            return 0
        settings = load_settings()
        db = RestDatabase(settings.supabase_url, settings.supabase_secret_key)
        summaries = import_files(db, args.files, args.period)
    except (ImportFileError, SettingsError, DatabaseError) as error:
        report.failure(title, str(error))
        return 1

    for path, summary in zip(args.files, summaries):
        report.result(f"{title}: {path.name}", summary.text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
