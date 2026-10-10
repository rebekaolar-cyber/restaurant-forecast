"""Shared test tools: saved weather answers, a fake web session, and a throwaway database.

The throwaway database is a real Postgres started just for the tests, with the real migrations
and seed applied. The tests talk to it as the nightly job's own database role, so the rights and
rules in supabase/migrations/ are tested too. It needs no network and no keys.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

import pytest

from forecast.db import Filter, check_filters, check_rows

REPO = Path(__file__).resolve().parents[2]
SAMPLES = Path(__file__).resolve().parent / "samples"
SEEDED_RESTAURANT = "35f0d253-0e43-4e2f-8c23-d52b4ca159f7"
PORT = 54330


def sample(name: str) -> dict:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------
# A fake web session: answers from a prepared list instead of the internet
# ------------------------------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code: int = 200, body=None, headers: dict | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def json(self):
        if self._body is None or isinstance(self._body, str):
            raise ValueError("not JSON")
        return self._body


class FakeSession:
    """Hands out prepared answers in order and remembers every request it was asked to make."""

    def __init__(self, answers: Sequence):
        self._answers = list(answers)
        self.calls: list[dict] = []

    def _next(self, call: dict):
        self.calls.append(call)
        if not self._answers:
            raise AssertionError(f"unexpected extra request: {call['method']} {call['url']}")
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def get(self, url, params=None, timeout=None):
        return self._next({"method": "GET", "url": url, "params": params, "timeout": timeout})

    def request(self, method, url, params=None, headers=None, json=None, timeout=None):
        return self._next(
            {"method": method, "url": url, "params": params, "headers": headers, "json": json, "timeout": timeout}
        )


# ------------------------------------------------------------------------------------------------
# A throwaway database
# ------------------------------------------------------------------------------------------------


class LocalDatabase:
    """Stands in for forecast.db.RestDatabase in tests.

    Same three methods, but it runs against the throwaway Postgres as the nightly job's role
    (service_role), using the same kind of SQL the Supabase web API builds from a request.
    """

    def __init__(self, connection):
        self._connection = connection

    def select(self, table: str, columns: str, filters: Sequence[Filter] = (), *, order: str) -> list[dict]:
        from psycopg import sql

        where, values = self._where(filters)
        query = sql.SQL("select coalesce(json_agg(t), '[]'::json) from (select {} from public.{}{} order by {}) t").format(
            sql.SQL(", ").join(sql.Identifier(c.strip()) for c in columns.split(",")),
            sql.Identifier(table),
            where,
            sql.Identifier(order),
        )
        return self._connection.execute(query, values).fetchone()[0]

    def count(self, table: str, filters: Sequence[Filter] = ()) -> int:
        from psycopg import sql

        where, values = self._where(filters)
        query = sql.SQL("select count(*) from public.{}{}").format(sql.Identifier(table), where)
        return self._connection.execute(query, values).fetchone()[0]

    def upsert(self, table: str, rows: Sequence[dict], *, on_conflict: Sequence[str]) -> None:
        from psycopg import sql
        from psycopg.types.json import Json

        check_rows(rows, on_conflict)
        if not rows:
            return
        columns = list(rows[0])
        updates = [c for c in columns if c not in on_conflict]
        action = (
            sql.SQL("do update set {}").format(
                sql.SQL(", ").join(sql.SQL("{0} = excluded.{0}").format(sql.Identifier(c)) for c in updates)
            )
            if updates
            else sql.SQL("do nothing")
        )
        query = sql.SQL(
            "insert into public.{table} ({columns}) "
            "select {columns} from json_populate_recordset(null::public.{table}, %s) "
            "on conflict ({conflict}) {action}"
        ).format(
            table=sql.Identifier(table),
            columns=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            conflict=sql.SQL(", ").join(sql.Identifier(c) for c in on_conflict),
            action=action,
        )
        self._connection.execute(query, [Json(list(rows))])

    @staticmethod
    def _where(filters: Sequence[Filter]):
        from psycopg import sql

        check_filters(filters)
        if not filters:
            return sql.SQL(""), []
        symbols = {"eq": "=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
        parts = [sql.SQL("{} {} %s").format(sql.Identifier(c), sql.SQL(symbols[op])) for c, op, _ in filters]
        return sql.SQL(" where ") + sql.SQL(" and ").join(parts), [value for _, _, value in filters]


def _postgres_programs() -> Path | None:
    configured = os.environ.get("PG_BIN")
    if configured:
        return Path(configured)
    found = sorted(Path("/usr/lib/postgresql").glob("*/bin"), key=lambda p: int(p.parent.name) if p.parent.name.isdigit() else 0)
    return found[-1] if found else None


@pytest.fixture(scope="session")
def local_postgres():
    """Starts a throwaway Postgres with the real migrations and seed. Yields how to connect."""
    pg_bin = _postgres_programs()
    if pg_bin is None or not (pg_bin / "initdb").exists():
        message = "Postgres server programs not found (set PG_BIN to the folder that holds initdb)"
        if os.environ.get("REQUIRE_LOCAL_POSTGRES"):
            pytest.fail(message)
        pytest.skip(message)

    work = Path(tempfile.mkdtemp(prefix="forecast-test-db-"))
    as_server: list[str] = []
    if os.geteuid() == 0:  # Postgres refuses to run as root
        shutil.chown(work, "postgres")
        as_server = ["runuser", "-u", "postgres", "--"]
    data = work / "data"

    def run(command: list[str]) -> None:
        subprocess.run(command, check=True, capture_output=True, text=True)

    def psql(*arguments: str) -> None:
        run(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", str(work), "-p", str(PORT), "-U", "postgres", "-d", "postgres", *arguments])

    try:
        run(as_server + [str(pg_bin / "initdb"), "-D", str(data), "-U", "postgres", "-A", "trust", "-E", "UTF8"])
        run(
            as_server
            + [str(pg_bin / "pg_ctl"), "-D", str(data), "-l", str(work / "server.log"), "-w",
               "-o", f"-p {PORT} -k {work} -c listen_addresses=''", "start"]
        )
        psql("-f", str(REPO / "supabase" / "tests" / "local_stub.sql"))
        for migration in sorted((REPO / "supabase" / "migrations").glob("*.sql")):
            psql("-f", str(migration))
        psql("-f", str(REPO / "supabase" / "seed.sql"))
        yield f"host={work} port={PORT} user=postgres dbname=postgres"
    finally:
        subprocess.run(as_server + [str(pg_bin / "pg_ctl"), "-D", str(data), "-m", "immediate", "stop"], capture_output=True)
        shutil.rmtree(work, ignore_errors=True)


@pytest.fixture
def owner(local_postgres):
    """A connection as the database owner, for preparing and inspecting test data."""
    import psycopg

    with psycopg.connect(local_postgres, autocommit=True) as connection:
        connection.execute("truncate public.daily_weather, public.bookings, public.receipts")
        yield connection


@pytest.fixture
def db(local_postgres, owner):
    """The throwaway database, used the way the nightly job uses the real one."""
    import psycopg

    with psycopg.connect(local_postgres, autocommit=True) as connection:
        connection.execute("set role service_role")
        yield LocalDatabase(connection)
