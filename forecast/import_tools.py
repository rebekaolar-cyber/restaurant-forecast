"""What the two importers (import_covers, import_rosters) share.

An import file is read completely and checked completely before anything is written. The first
check is the header: it has to be exactly the one we expect. A file with an extra column is
refused, whatever the column holds, because an extra column is how a name, a phone number or an
email would slip into the database.

The importers can also print SQL instead of writing (`--sql`). That SQL carries only the numbers
and labels of the file, never the file's name or path, so it can be pasted into the Supabase SQL
editor or the connector without the file itself ever entering the repo.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from forecast.db import Database

PREFIX = "restaurant "   # a restaurant called "Restaurant X" in the database also answers to "X"


class ImportFileError(RuntimeError):
    """The file cannot be imported: wrong header, a value that makes no sense, unknown restaurant."""


# ------------------------------------------------------------------------------------------------
# Reading a file
# ------------------------------------------------------------------------------------------------


def read_csv(path: Path, header: Sequence[str], optional: Sequence[str] = ()) -> list[dict[str, str]]:
    """The rows of a CSV file whose header is exactly `header` (plus, at most, the `optional`
    columns, in order, after it). Any other header is refused with the column names spelled out."""
    try:
        text = path.read_text(encoding="utf-8-sig")   # utf-8-sig also eats the marker Excel adds
    except OSError as error:
        raise ImportFileError(f"{path.name}: cannot be read ({type(error).__name__})") from None
    except UnicodeDecodeError:
        raise ImportFileError(f"{path.name}: is not a UTF-8 text file") from None

    reader = csv.reader(text.splitlines())
    found = [column.strip() for column in next(reader, [])]
    allowed = [*header, *optional]
    unexpected = [column for column in found if column not in allowed]
    missing = [column for column in header if column not in found]
    in_order = found == allowed[: len(found)]
    if unexpected or missing or not in_order:
        problems = []
        if unexpected:
            problems.append(f"unexpected column(s): {', '.join(repr(c) for c in unexpected)}")
        if missing:
            problems.append(f"missing column(s): {', '.join(repr(c) for c in missing)}")
        if not problems:
            problems.append("the columns are not in the expected order")
        raise ImportFileError(
            f"{path.name}: refused, the header is not the one expected. "
            f"{'; '.join(problems)}. Expected exactly: {','.join(header)}"
            + (f" (optionally followed by {','.join(optional)})" if optional else "")
        )

    rows = []
    for number, values in enumerate(reader, start=2):
        if not values or all(not value.strip() for value in values):
            continue   # an empty line
        if len(values) != len(found):
            raise ImportFileError(f"{path.name} line {number}: {len(values)} values, but the header has {len(found)}")
        rows.append(dict(zip(found, (value.strip() for value in values))))
    if not rows:
        raise ImportFileError(f"{path.name}: has a header but no rows")
    return rows


def parse_date(text: str, where: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ImportFileError(f"{where}: {text!r} is not a date written as YYYY-MM-DD") from None


def parse_count(text: str, where: str) -> int:
    if not re.fullmatch(r"\d+", text):
        raise ImportFileError(f"{where}: {text!r} is not a whole number of 0 or more")
    return int(text)


# ------------------------------------------------------------------------------------------------
# Which restaurant?
# ------------------------------------------------------------------------------------------------


def _answers_to(restaurant_name: str, wanted: str) -> bool:
    """Does the restaurant called `restaurant_name` answer to `wanted`? Case does not matter, and
    "Restaurant Habibi" also answers to "Habibi", because that is how TheFork writes it."""
    name, wanted = restaurant_name.strip().casefold(), wanted.strip().casefold()
    return name == wanted or (name.startswith(PREFIX) and name[len(PREFIX):].strip() == wanted)


def find_restaurant(wanted: str, restaurants: Sequence[dict]) -> dict:
    """The one restaurant row that answers to `wanted`. Anything else is an error."""
    matches = [r for r in restaurants if _answers_to(r["name"], wanted)]
    if len(matches) == 1:
        return matches[0]
    known = ", ".join(sorted(repr(r["name"]) for r in restaurants)) or "none"
    if not matches:
        raise ImportFileError(f"no restaurant called {wanted!r} in the restaurants table (known: {known})")
    raise ImportFileError(f"more than one restaurant answers to {wanted!r} (known: {known})")


def load_restaurants(db: Database) -> list[dict]:
    return db.select("restaurants", "id,name", order="name")


# ------------------------------------------------------------------------------------------------
# Printing SQL instead of writing
# ------------------------------------------------------------------------------------------------


def sql_literal(value: object) -> str:
    """A value as a SQL literal. Text is quoted the standard way; a quote inside is doubled."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, date):
        return f"'{value.isoformat()}'"
    text = str(value)
    if "\x00" in text:
        raise ImportFileError("a value contains a NUL character, which the database cannot store")
    return "'" + text.replace("'", "''") + "'"


def restaurant_condition_sql(wanted: str | None) -> str:
    """The SQL condition that picks the restaurant row, the same way find_restaurant does.
    With no name, the database must hold exactly one restaurant and that one is meant."""
    if wanted is None:
        return "true"
    name = sql_literal(wanted.strip().casefold())
    return f"(lower(r.name) = {name} or lower(r.name) = {sql_literal(PREFIX)} || {name})"


def restaurant_guard_sql(wanted: str | None) -> str:
    """A statement that stops the whole script unless exactly one restaurant matches."""
    described = "exactly one restaurant" if wanted is None else f"a restaurant called {wanted.strip()!r}"
    message = sql_literal(f"import stopped: the restaurants table does not hold {described}")
    return (
        "do $$ begin\n"
        f"  if (select count(*) from public.restaurants r where {restaurant_condition_sql(wanted)}) <> 1 then\n"
        f"    raise exception using message = {message};\n"
        "  end if;\n"
        "end $$;"
    )


def upsert_sql(table: str, rows: Sequence[dict], on_conflict: Sequence[str], restaurant: str | None) -> list[str]:
    """One insert-or-update statement per row. restaurant_id is looked up by name in the
    database itself, so the printed SQL never has to know an id."""
    statements = []
    for row in rows:
        columns = ["restaurant_id", *row]
        values = ["r.id", *(sql_literal(row[column]) for column in row)]
        updates = [column for column in row if column not in on_conflict]
        action = (
            "do update set " + ", ".join(f"{column} = excluded.{column}" for column in updates)
            if updates
            else "do nothing"
        )
        statements.append(
            f"insert into public.{table} ({', '.join(columns)})\n"
            f"  select {', '.join(values)}\n"
            f"  from public.restaurants r where {restaurant_condition_sql(restaurant)}\n"
            f"  on conflict ({', '.join(on_conflict)}) {action};"
        )
    return statements


def sql_script(blocks: Sequence[tuple[str, str | None, list[str]]]) -> str:
    """A whole script: one transaction, a guard per restaurant, then the statements.
    Each block is (a comment line without any file name or path, restaurant name, statements)."""
    lines = ["begin;"]
    guarded: set[str | None] = set()
    for comment, restaurant, statements in blocks:
        lines.append(f"-- {comment}")
        if restaurant not in guarded:
            lines.append(restaurant_guard_sql(restaurant))
            guarded.add(restaurant)
        lines.extend(statements)
    lines.append("commit;")
    return "\n".join(lines) + "\n"
