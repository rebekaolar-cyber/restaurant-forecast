"""Tests for writing the forecast and for the whole nightly job, on the throwaway database."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from forecast import fake_history as fh
from forecast import nightly, predict, staffing
from forecast.backtest import OFFLINE_BANDS
from forecast.baseline import ForecastError
from forecast.tests.conftest import (
    HABIBI,
    SEEDED_RESTAURANT,
    FakeResponse,
    FakeSession,
    open_meteo_answer,
    put_weather,
)

TZ = ZoneInfo("Europe/Amsterdam")
AS_OF = datetime(2026, 10, 10, 3, 0, tzinfo=TZ)
TODAY = date(2026, 10, 10)
FIRST_DAY = date(2026, 6, 1)


def no_sleep(_seconds):
    pass


def weather_answers(today: date = TODAY) -> list[FakeResponse]:
    """What Open-Meteo would answer the nightly job: 30 days measured, then 10 days back plus 14 ahead."""
    return [
        FakeResponse(200, open_meteo_answer(today - timedelta(days=30), today - timedelta(days=1))),
        FakeResponse(200, open_meteo_answer(today - timedelta(days=10), today + timedelta(days=13))),
    ]


def forecasts(owner):
    return owner.execute(
        "select date, predicted_guests, servers, bar_staff, runners, food_staff, cooks, model, created_at "
        "from public.forecasts order by date"
    ).fetchall()


@pytest.fixture
def with_history(db, owner):
    """Four months of weather, bookings and receipts in the database, as of the night of 10 October."""
    put_weather(owner, FIRST_DAY, date(2026, 10, 23))
    fh.top_up_all(db, as_of=AS_OF)
    return db


# ---- writing the forecast ---------------------------------------------------------------------


def test_writes_fourteen_evenings_with_staff_from_the_managers_table(with_history, owner):
    summary = predict.predict_all(with_history, as_of=AS_OF)[0]

    rows = forecasts(owner)
    assert [row[0] for row in rows] == [TODAY + timedelta(days=n) for n in range(14)]
    assert summary.first_day == TODAY and summary.last_day == date(2026, 10, 23)
    for day, guests, servers, bar_staff, runners, food_staff, cooks, model, created_at in rows:
        assert model == "baseline" and created_at == AS_OF
        assert staffing.staff_for(guests, OFFLINE_BANDS) == {
            "servers": servers, "bar_staff": bar_staff, "runners": runners, "food_staff": food_staff, "cooks": cooks,
        }
        assert cooks == 4
    by_weekday = {row[0].weekday(): row[1] for row in rows[:7]}
    assert by_weekday[5] > by_weekday[4] > by_weekday[6] > by_weekday[0]    # Sat > Fri > Sun > Mon
    assert 120 < by_weekday[4] < 230                                         # a Friday near the real 174
    assert summary.guests == tuple(row[1] for row in rows)


def test_running_it_again_changes_nothing_and_the_next_night_moves_on(with_history, owner):
    predict.predict_all(with_history, as_of=AS_OF)
    first = forecasts(owner)
    predict.predict_all(with_history, as_of=AS_OF)
    assert forecasts(owner) == first

    put_weather(owner, TODAY, TODAY, measured_through=TODAY)
    fh.top_up_all(with_history, as_of=AS_OF + timedelta(days=1))
    predict.predict_all(with_history, as_of=AS_OF + timedelta(days=1))
    later = forecasts(owner)
    assert len(later) == 15                              # one new evening: 24 October
    assert later[0] == first[0]                          # the evening that is over keeps its last forecast
    assert all(row[8] == AS_OF + timedelta(days=1) for row in later[1:])


def test_the_forecast_never_touches_overrides_and_cannot(with_history, owner):
    owner.execute(
        "insert into public.forecast_overrides (restaurant_id, date, servers, runners, note) values (%s, %s, 9, 5, 'party')",
        [SEEDED_RESTAURANT, TODAY],
    )
    before = owner.execute("select * from public.forecast_overrides").fetchall()

    predict.predict_all(with_history, as_of=AS_OF)

    assert owner.execute("select * from public.forecast_overrides").fetchall() == before
    import psycopg

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with_history.upsert(
            "forecast_overrides",
            [{"restaurant_id": SEEDED_RESTAURANT, "date": TODAY.isoformat(), "shift": "dinner", "servers": 1}],
            on_conflict=["restaurant_id", "date", "shift"],
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with_history.delete("forecast_overrides", [("restaurant_id", "eq", SEEDED_RESTAURANT)])


def test_without_history_it_refuses_and_leaves_the_table_as_it_was(db, owner):
    before = forecasts(owner)
    with pytest.raises(ForecastError, match="only 0 earlier"):
        predict.predict_all(db, as_of=AS_OF)
    assert forecasts(owner) == before and {row[7] for row in before} == {"placeholder"}


def test_a_forecast_that_forgets_a_role_is_refused_by_the_database(with_history):
    import psycopg

    with pytest.raises(psycopg.errors.NotNullViolation):
        with_history.upsert(
            "forecasts",
            [{"restaurant_id": SEEDED_RESTAURANT, "date": "2027-01-01", "shift": "dinner", "predicted_guests": 100,
              "servers": 3, "cooks": 4, "model": "baseline"}],
            on_conflict=["restaurant_id", "date", "shift"],
        )


# ---- the whole nightly job --------------------------------------------------------------------


def test_the_nightly_job_runs_weather_then_bookings_then_forecast(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 9, 9))    # older weather is there; the job loads the rest
    session = FakeSession(weather_answers())

    nightly.run(db, session, as_of=AS_OF, fake_feed=True, sleep=no_sleep)

    assert len(session.calls) == 2
    weather = owner.execute("select count(*), count(*) filter (where is_forecast) from public.daily_weather where date >= '2026-09-10'").fetchone()
    assert weather == (44, 14)
    assert owner.execute("select count(*) from public.bookings").fetchone()[0] > 3000
    assert owner.execute("select max(opened_at) < %s from public.receipts", [AS_OF]).fetchone()[0] is True
    rows = forecasts(owner)
    assert len(rows) == 14 and {row[7] for row in rows} == {"baseline"}


def test_a_repeat_run_of_the_nightly_job_adds_nothing(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 9, 9))
    nightly.run(db, FakeSession(weather_answers()), as_of=AS_OF, fake_feed=True, sleep=no_sleep)
    counts = "select (select count(*) from public.daily_weather), (select count(*) from public.bookings), (select count(*) from public.receipts), (select count(*) from public.forecasts)"
    before = owner.execute(counts).fetchone()
    snapshot = forecasts(owner)

    nightly.run(db, FakeSession(weather_answers()), as_of=AS_OF, fake_feed=True, expect_unchanged=True, sleep=no_sleep)

    assert owner.execute(counts).fetchone() == before
    assert forecasts(owner) == snapshot


def test_when_the_weather_service_is_down_the_job_stops_and_says_where(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 9, 9))
    session = FakeSession([FakeResponse(503, "busy")] * 3)

    with pytest.raises(nightly.NightlyError, match="Weather failed: the weather service answered HTTP 503"):
        nightly.run(db, session, as_of=AS_OF, fake_feed=True, sleep=no_sleep)

    # Nothing after the failed step ran.
    assert owner.execute("select count(*) from public.bookings").fetchone()[0] == 0
    assert {row[7] for row in forecasts(owner)} == {"placeholder"}


def test_when_there_is_no_history_the_forecast_step_fails_loudly(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 9, 9))
    with pytest.raises(nightly.NightlyError, match="Forecast failed: only 0 earlier"):
        nightly.run(db, FakeSession(weather_answers()), as_of=AS_OF, fake_feed=False, sleep=no_sleep)


def test_the_command_exits_with_an_error_and_a_message_on_the_run_page(monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert nightly.main(["--fake-feed"]) == 1
    assert "::error title=Nightly job::Missing%3A SUPABASE_URL".replace("%3A", ":") in capsys.readouterr().out
