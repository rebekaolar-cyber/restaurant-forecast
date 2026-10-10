"""A small client for the Supabase web API. It does only what the nightly job needs:
read rows, count rows, and insert-or-update rows.

It talks to the database over HTTPS with the secret key. What that key may touch is decided by
the rights in supabase/migrations/, not here.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any, Protocol

import requests

from forecast.settings import key_role

# One condition on a column: (column, operator, value), for example ("date", "gte", "2026-01-01").
Filter = tuple[str, str, Any]
OPERATORS = {"eq", "gt", "gte", "lt", "lte"}

PAGE_SIZE = 1000   # Supabase returns at most 1000 rows per request
CHUNK_SIZE = 500   # rows sent per insert-or-update request
ATTEMPTS = 3
TIMEOUT_SECONDS = 30


class DatabaseError(RuntimeError):
    """The database refused a request or could not be reached."""


class Database(Protocol):
    """The three things the forecast code may ask of a database."""

    def select(self, table: str, columns: str, filters: Sequence[Filter] = (), *, order: str) -> list[dict]: ...

    def count(self, table: str, filters: Sequence[Filter] = ()) -> int: ...

    def upsert(self, table: str, rows: Sequence[dict], *, on_conflict: Sequence[str]) -> None: ...


def as_text(value: Any) -> str:
    """Writes a value the way the web API expects it in a condition."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def check_filters(filters: Sequence[Filter]) -> None:
    for column, operator, _ in filters:
        if operator not in OPERATORS:
            raise ValueError(f"Unknown operator {operator!r} for column {column!r}")


def check_rows(rows: Sequence[dict], on_conflict: Sequence[str]) -> None:
    """Catches the two mistakes that would make an insert-or-update fail or do the wrong thing."""
    if not on_conflict:
        raise ValueError("on_conflict must name the columns that identify a row")
    if not rows:
        return
    columns = set(rows[0])
    if any(set(row) != columns for row in rows):
        raise ValueError("Every row must have exactly the same columns")
    if not set(on_conflict) <= columns:
        raise ValueError("Every row must contain the on_conflict columns")
    keys = {tuple(as_text(row[column]) for column in on_conflict) for row in rows}
    if len(keys) != len(rows):
        raise ValueError(f"The same {', '.join(on_conflict)} appears more than once in the rows")


class RestDatabase:
    """The real database, reached through the Supabase web API."""

    def __init__(
        self,
        url: str,
        secret_key: str,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base = f"{url.rstrip('/')}/rest/v1"
        self._session = session or requests.Session()
        self._sleep = sleep
        # New keys go in the apikey header only. Old-style keys must also be sent as a login token.
        self._headers = {"apikey": secret_key}
        if not secret_key.startswith("sb_") and key_role(secret_key) == "secret":
            self._headers["Authorization"] = f"Bearer {secret_key}"

    def select(self, table: str, columns: str, filters: Sequence[Filter] = (), *, order: str) -> list[dict]:
        """All matching rows, fetched page by page. `order` keeps the pages stable."""
        check_filters(filters)
        rows: list[dict] = []
        while True:
            params = [("select", columns), ("order", order), ("limit", str(PAGE_SIZE)), ("offset", str(len(rows)))]
            params += self._conditions(filters)
            page = self._request("GET", table, params=params).json()
            rows.extend(page)
            if len(page) < PAGE_SIZE:
                return rows

    def count(self, table: str, filters: Sequence[Filter] = ()) -> int:
        check_filters(filters)
        response = self._request(
            "HEAD", table, params=[("select", "*")] + self._conditions(filters), headers={"Prefer": "count=exact"}
        )
        content_range = response.headers.get("Content-Range", "")  # looks like "0-24/745" or "*/0"
        total = content_range.rpartition("/")[2]
        if not total.isdigit():
            raise DatabaseError(f"count {table} failed: the database did not say how many rows there are")
        return int(total)

    def upsert(self, table: str, rows: Sequence[dict], *, on_conflict: Sequence[str]) -> None:
        """Insert rows; where a row with the same on_conflict columns exists, update it instead.

        This is what makes running a job twice safe: the second run updates, it never duplicates.
        """
        check_rows(rows, on_conflict)
        for start in range(0, len(rows), CHUNK_SIZE):
            self._request(
                "POST",
                table,
                params=[("on_conflict", ",".join(on_conflict))],
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json=list(rows[start : start + CHUNK_SIZE]),
            )

    @staticmethod
    def _conditions(filters: Sequence[Filter]) -> list[tuple[str, str]]:
        return [(column, f"{operator}.{as_text(value)}") for column, operator, value in filters]

    def _request(self, method: str, table: str, *, params=None, headers=None, json=None) -> requests.Response:
        problem = "no attempt was made"
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = self._session.request(
                    method,
                    f"{self._base}/{table}",
                    params=params,
                    headers={**self._headers, **(headers or {})},
                    json=json,
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException as error:
                problem = f"could not reach the database ({type(error).__name__})"
            else:
                if response.status_code < 300:
                    return response
                problem = f"HTTP {response.status_code}: {self._explain(response)}"
                if response.status_code < 500 and response.status_code != 429:
                    break  # our own mistake or a refusal: trying again will not help
            if attempt < ATTEMPTS:
                self._sleep(2 * attempt)
        raise DatabaseError(f"{method} {table} failed: {problem}")

    @staticmethod
    def _explain(response: requests.Response) -> str:
        """The database's own error message, without the part that can echo row contents."""
        try:
            body = response.json()
        except ValueError:
            return "no explanation given"
        if not isinstance(body, dict):
            return "no explanation given"
        parts = [str(body[name]) for name in ("code", "message", "hint") if body.get(name)]
        return " | ".join(parts) or "no explanation given"
