"""Tests for the Supabase web API client: are the right requests built, and are errors loud?"""

from __future__ import annotations

import base64
from datetime import date

import pytest
import requests

from forecast.db import DatabaseError, RestDatabase
from forecast.tests.conftest import FakeResponse, FakeSession

URL = "https://example.supabase.co"
KEY = "sb_secret_TESTONLY-not-a-real-key"


def make(answers, key=KEY):
    session = FakeSession(answers)
    return RestDatabase(URL, key, session=session, sleep=lambda _seconds: None), session


def old_style_key(role: str) -> str:
    payload = base64.urlsafe_b64encode(('{"role":"%s"}' % role).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


def test_select_builds_conditions_and_sends_the_key_as_apikey_only():
    db, session = make([FakeResponse(200, [{"date": "2026-10-10"}])])
    rows = db.select(
        "daily_weather",
        "date,temp_max",
        [("restaurant_id", "eq", "abc"), ("date", "gte", date(2026, 10, 1)), ("is_forecast", "eq", True)],
        order="date",
    )
    assert rows == [{"date": "2026-10-10"}]
    call = session.calls[0]
    assert (call["method"], call["url"]) == ("GET", f"{URL}/rest/v1/daily_weather")
    assert call["params"] == [
        ("select", "date,temp_max"),
        ("order", "date"),
        ("limit", "1000"),
        ("offset", "0"),
        ("restaurant_id", "eq.abc"),
        ("date", "gte.2026-10-01"),
        ("is_forecast", "eq.true"),
    ]
    assert call["headers"] == {"apikey": KEY}
    assert call["timeout"] == 30


def test_old_style_secret_key_is_also_sent_as_a_login_token():
    key = old_style_key("service_role")
    db, session = make([FakeResponse(200, [])], key=key)
    db.select("restaurants", "id", order="id")
    assert session.calls[0]["headers"] == {"apikey": key, "Authorization": f"Bearer {key}"}


def test_select_fetches_every_page():
    full_page = [{"n": n} for n in range(1000)]
    db, session = make([FakeResponse(200, full_page), FakeResponse(200, full_page), FakeResponse(200, [{"n": 1}])])
    assert len(db.select("bookings", "n", order="n")) == 2001
    assert [dict(call["params"])["offset"] for call in session.calls] == ["0", "1000", "2000"]


def test_select_rejects_an_unknown_operator():
    db, _ = make([])
    with pytest.raises(ValueError, match="Unknown operator"):
        db.select("bookings", "id", [("id", "like", "x")], order="id")


def test_count_reads_the_total_from_the_answer():
    db, session = make([FakeResponse(200, None, {"Content-Range": "0-24/745"}), FakeResponse(200, None, {"Content-Range": "*/0"})])
    assert db.count("daily_weather", [("restaurant_id", "eq", "abc")]) == 745
    assert db.count("daily_weather") == 0
    assert session.calls[0]["method"] == "HEAD"
    assert session.calls[0]["headers"]["Prefer"] == "count=exact"


def test_count_fails_loudly_without_a_total():
    db, _ = make([FakeResponse(200, None, {})])
    with pytest.raises(DatabaseError, match="did not say how many rows"):
        db.count("daily_weather")


def test_upsert_sends_rows_in_chunks_as_insert_or_update():
    rows = [{"restaurant_id": "abc", "date": f"day-{n}", "temp_max": 1.0} for n in range(1200)]
    db, session = make([FakeResponse(201)] * 3)
    db.upsert("daily_weather", rows, on_conflict=["restaurant_id", "date"])
    assert [len(call["json"]) for call in session.calls] == [500, 500, 200]
    call = session.calls[0]
    assert (call["method"], call["url"]) == ("POST", f"{URL}/rest/v1/daily_weather")
    assert call["params"] == [("on_conflict", "restaurant_id,date")]
    assert call["headers"]["Prefer"] == "resolution=merge-duplicates,return=minimal"


def test_upsert_with_no_rows_sends_nothing():
    db, session = make([])
    db.upsert("daily_weather", [], on_conflict=["restaurant_id", "date"])
    assert session.calls == []


@pytest.mark.parametrize(
    "rows, message",
    [
        ([{"a": 1, "b": 2}, {"a": 1}], "exactly the same columns"),
        ([{"a": 1, "b": 2}, {"a": 1, "b": 3}], "appears more than once"),
        ([{"b": 2}], "must contain the on_conflict columns"),
    ],
)
def test_upsert_refuses_rows_that_would_go_wrong(rows, message):
    db, session = make([])
    with pytest.raises(ValueError, match=message):
        db.upsert("t", rows, on_conflict=["a"])
    assert session.calls == []


def test_a_refusal_is_reported_without_row_contents_or_the_key():
    refusal = {
        "code": "42501",
        "message": "permission denied for table forecast_overrides",
        "details": "Failing row contains (secret-looking row data)",
        "hint": None,
    }
    db, session = make([FakeResponse(403, refusal)])
    with pytest.raises(DatabaseError) as caught:
        db.upsert("forecast_overrides", [{"a": 1}], on_conflict=["a"])
    text = str(caught.value)
    assert text == "POST forecast_overrides failed: HTTP 403: 42501 | permission denied for table forecast_overrides"
    assert KEY not in text and "Failing row" not in text
    assert len(session.calls) == 1  # a refusal is not retried


def test_tries_again_when_the_database_is_briefly_unavailable():
    db, session = make([FakeResponse(503, "busy"), requests.ConnectionError("down"), FakeResponse(200, [])])
    assert db.select("restaurants", "id", order="id") == []
    assert len(session.calls) == 3


def test_gives_up_after_three_tries_and_says_why():
    db, _ = make([requests.ConnectionError(f"could not connect using {KEY}")] * 3)
    with pytest.raises(DatabaseError) as caught:
        db.select("restaurants", "id", order="id")
    assert "could not reach the database (ConnectionError)" in str(caught.value)
    assert KEY not in str(caught.value)


def test_select_with_a_limit_and_newest_first_asks_for_just_that():
    db, session = make([FakeResponse(200, [{"opened_at": "2026-10-09T20:00:00+00:00"}])])
    rows = db.select("receipts", "opened_at", [("restaurant_id", "eq", "abc")], order="opened_at.desc", limit=1)
    assert len(rows) == 1 and len(session.calls) == 1
    assert session.calls[0]["params"][:4] == [("select", "opened_at"), ("order", "opened_at.desc"), ("limit", "1"), ("offset", "0")]


def test_a_limit_larger_than_a_page_is_fetched_in_pages():
    page = [{"n": n} for n in range(1000)]
    db, session = make([FakeResponse(200, page), FakeResponse(200, page[:500])])
    assert len(db.select("bookings", "n", order="n", limit=1500)) == 1500
    assert [dict(call["params"])["limit"] for call in session.calls] == ["1000", "500"]


def test_a_moment_in_time_is_sent_as_utc():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    three_at_night = datetime(2026, 10, 10, 3, 0, tzinfo=ZoneInfo("Europe/Amsterdam"))
    db, session = make([FakeResponse(200, [])])
    db.select("receipts", "guests", [("opened_at", "lt", three_at_night)], order="opened_at")
    assert ("opened_at", "lt.2026-10-10T01:00:00Z") in session.calls[0]["params"]
    with pytest.raises(ValueError, match="without a timezone"):
        db.select("receipts", "guests", [("opened_at", "lt", datetime(2026, 10, 10, 3, 0))], order="opened_at")


def test_delete_needs_a_condition_and_sends_only_that():
    db, session = make([FakeResponse(204)])
    with pytest.raises(ValueError, match="at least one condition"):
        db.delete("bookings", [])
    assert session.calls == []
    db.delete("bookings", [("restaurant_id", "eq", "abc")])
    call = session.calls[0]
    assert (call["method"], call["url"], call["params"]) == ("DELETE", f"{URL}/rest/v1/bookings", [("restaurant_id", "eq.abc")])
