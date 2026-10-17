"""Imports the manager's planned staff per role per evening into the rosters table.

    python -m forecast.import_rosters FILE                       write to the database
    python -m forecast.import_rosters FILE --restaurant Habibi   when the database holds more
                                                                 than one restaurant
    python -m forecast.import_rosters FILE --sql > rosters.sql   print SQL instead of writing

The file is a CSV we define ourselves, counts only. Exactly these columns, in this order:

    date,role,planned_count

with, optionally, a fourth column `source` (where the numbers came from; 'manual' when left
out). One row per evening and role. `role` is one of servers, bar_staff, runners, food_staff,
cooks, or the roster's own letter: W (floor) = servers, B (bar) = bar_staff, R (runner) =
runners, F (food) = food_staff, K (kitchen) = cooks.

A file with any other header is refused. A roster file that names people is not a roster file
for this importer: it never gets in.

Running the same file twice changes nothing: a row that is already there is updated, never
doubled. The whole file is checked before anything is written; one bad value and nothing is
written at all.

Needs SUPABASE_URL and SUPABASE_SECRET_KEY in the environment, except with --sql.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
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

TABLE = "rosters"
SHIFT = "dinner"
DEFAULT_SOURCE = "manual"
HEADER = ("date", "role", "planned_count")
OPTIONAL = ("source",)
ROLES = ("servers", "bar_staff", "runners", "food_staff", "cooks")
LETTERS = {"W": "servers", "B": "bar_staff", "R": "runners", "F": "food_staff", "K": "cooks"}
KEY = ("restaurant_id", "date", "shift", "role")


@dataclass(frozen=True)
class RosterFile:
    rows: list[dict]           # table rows without restaurant_id, in file order

    @property
    def first_day(self) -> date:
        return min(row["date"] for row in self.rows)

    @property
    def last_day(self) -> date:
        return max(row["date"] for row in self.rows)


@dataclass(frozen=True)
class ImportSummary:
    rows_read: int
    rows_written: int
    first_day: date
    last_day: date
    evenings: int
    rows_before: int | None = None
    rows_after: int | None = None

    def text(self) -> str:
        text = (
            f"{self.rows_read} rows read, {self.rows_written} rows written "
            f"({self.evenings} evenings, {self.first_day} to {self.last_day})."
        )
        if self.rows_before is not None:
            text += f" Rows in the table: {self.rows_before} before, {self.rows_after} after."
        return text


def parse_role(text: str, where: str) -> str:
    if text in ROLES:
        return text
    if text.upper() in LETTERS and len(text) == 1:
        return LETTERS[text.upper()]
    raise ImportFileError(
        f"{where}: {text!r} is not a role. Use one of {', '.join(ROLES)} or a roster letter "
        f"({', '.join(f'{letter} = {role}' for letter, role in LETTERS.items())})"
    )


def read_file(path: Path) -> RosterFile:
    """Reads and checks one roster file. Raises ImportFileError on the first problem."""
    raw = read_csv(path, HEADER, OPTIONAL)
    rows = []
    for n, row in enumerate(raw, start=2):
        where = f"{path.name} line {n}"
        rows.append(
            {
                "date": parse_date(row["date"], where),
                "shift": SHIFT,
                "role": parse_role(row["role"], where),
                "planned_count": parse_count(row["planned_count"], f"{where}, planned_count"),
                "source": row.get("source") or DEFAULT_SOURCE,
            }
        )
    repeated = [key for key, count in Counter((row["date"], row["role"]) for row in rows).items() if count > 1]
    if repeated:
        day, role = repeated[0]
        raise ImportFileError(f"{path.name}: {role} on {day} appears more than once")
    return RosterFile(rows=rows)


def summary_of(checked: RosterFile, before: int | None = None, after: int | None = None) -> ImportSummary:
    return ImportSummary(
        rows_read=len(checked.rows), rows_written=len(checked.rows),
        first_day=checked.first_day, last_day=checked.last_day,
        evenings=len({row["date"] for row in checked.rows}),
        rows_before=before, rows_after=after,
    )


def choose_restaurant(restaurants: list[dict], wanted: str | None) -> dict:
    """The restaurant the file is for: the one named, or the only one there is."""
    if wanted is not None:
        return find_restaurant(wanted, restaurants)
    if len(restaurants) == 1:
        return restaurants[0]
    known = ", ".join(sorted(repr(r["name"]) for r in restaurants)) or "none"
    raise ImportFileError(f"the database holds {len(restaurants)} restaurants (known: {known}); say which with --restaurant")


def import_file(db: Database, path: Path, restaurant_name: str | None = None) -> ImportSummary:
    checked = read_file(path)
    restaurant = choose_restaurant(load_restaurants(db), restaurant_name)
    mine = [("restaurant_id", "eq", restaurant["id"])]
    before = db.count(TABLE, mine)
    rows = [{"restaurant_id": restaurant["id"], **row, "date": row["date"].isoformat()} for row in checked.rows]
    db.upsert(TABLE, rows, on_conflict=KEY)
    return summary_of(checked, before, db.count(TABLE, mine))


def sql_for_file(path: Path, restaurant_name: str | None = None) -> tuple[str, ImportSummary]:
    """The SQL that would do the import, and the summary. Nothing about the file but its
    contents goes into the SQL: no name, no path."""
    checked = read_file(path)
    summary = summary_of(checked)
    script = sql_script([(f"rosters: {summary.text()}", restaurant_name, upsert_sql(TABLE, checked.rows, KEY, restaurant_name))])
    return script, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import the manager's planned staff per role per evening into rosters.")
    parser.add_argument("file", type=Path, metavar="FILE", help="CSV with the columns date,role,planned_count[,source]")
    parser.add_argument("--restaurant", help="the restaurant's name, when the database holds more than one")
    parser.add_argument("--sql", action="store_true", help="print SQL to stdout instead of writing to the database")
    args = parser.parse_args(argv)
    title = "Roster import"

    try:
        if args.sql:
            script, summary = sql_for_file(args.file, args.restaurant)
            sys.stdout.write(script)
            print(f"{title}: {args.file.name}: {summary.text()}", file=sys.stderr)
            return 0
        settings = load_settings()
        db = RestDatabase(settings.supabase_url, settings.supabase_secret_key)
        summary = import_file(db, args.file, args.restaurant)
    except (ImportFileError, SettingsError, DatabaseError) as error:
        report.failure(title, str(error))
        return 1

    report.result(f"{title}: {args.file.name}", summary.text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
