"""Tests for the weather loader, against real saved answers from Open-Meteo.

The saved answers were fetched on 10 October 2026, so "today" in these tests is that day.
"""

from __future__ import annotations

import copy
from datetime import date, timedelta

import pytest
import requests

from forecast import weather
from forecast.tests.conftest import SEEDED_RESTAURANT, FakeResponse, FakeSession, sample

TODAY = date(2026, 10, 10)
ARCHIVE = "open_meteo_archive_2026-09-30_to_2026-10-09.json"
FORECAST = "open_meteo_forecast_on_2026-10-10.json"
RESTAURANT = {
    "id": SEEDED_RESTAURANT,
    "name": "Restaurant Habibi",
    "latitude": 52.2066,
    "longitude": 6.8914,
    "timezone": "Europe/Amsterdam",
}


def no_sleep(_seconds):
    pass


def session_with(*payloads) -> FakeSession:
    return FakeSession([FakeResponse(200, payload) for payload in payloads])


def one_day_later(archive: dict, forecast: dict) -> tuple[dict, dict]:
    """What the service would answer the next day: every window has moved one day on."""
    archive, forecast = copy.deepcopy(archive), copy.deepcopy(forecast)
    # The archive now also knows 10 October: a measured 15.5 degrees and 2.2 mm of rain.
    for name, value in (("time", "2026-10-10"), ("temperature_2m_max", 15.5), ("precipitation_sum", 2.2),
                        ("wind_speed_10m_max", 20.0), ("sunshine_duration", 18000.0)):
        archive["daily"][name] = archive["daily"][name][1:] + [value]
    # The forecast drops its oldest day and reaches one day further, to 24 October.
    for name, value in (("time", "2026-10-24"), ("temperature_2m_max", 13.0), ("precipitation_sum", 0.4),
                        ("wind_speed_10m_max", 11.0), ("sunshine_duration", 9000.0)):
        forecast["daily"][name] = forecast["daily"][name][1:] + [value]
    return archive, forecast


# ---- reading an answer ------------------------------------------------------------------------


def test_reads_a_real_archive_answer():
    days = weather.parse_daily(sample(ARCHIVE))
    assert list(days)[0] == date(2026, 9, 30) and list(days)[-1] == date(2026, 10, 9)
    assert len(days) == 10
    # 37015.43 seconds of sunshine is 10.3 hours
    assert days[date(2026, 9, 30)] == {"temp_max": 27.0, "rain_mm": 0.0, "wind_max": 13.9, "sunshine_hours": 10.3}
    assert days[date(2026, 10, 9)] == {"temp_max": 14.7, "rain_mm": 9.3, "wind_max": 29.9, "sunshine_hours": 0.0}


def test_reads_a_real_forecast_answer():
    days = weather.parse_daily(sample(FORECAST))
    assert len(days) == 24  # 10 days back plus 14 days ahead
    assert list(days)[-1] == date(2026, 10, 23)
    assert days[TODAY]["temp_max"] == 14.2


def test_keeps_gaps_as_gaps():
    payload = sample(ARCHIVE)
    payload["daily"]["sunshine_duration"][3] = None
    assert weather.parse_daily(payload)[date(2026, 10, 3)]["sunshine_hours"] is None


def test_stops_when_a_unit_changes():
    payload = sample(ARCHIVE)
    payload["daily_units"]["wind_speed_10m_max"] = "mp/h"
    with pytest.raises(weather.WeatherError, match="wind_speed_10m_max is in 'mp/h'"):
        weather.parse_daily(payload)


def test_stops_when_a_list_is_too_short():
    payload = sample(ARCHIVE)
    payload["daily"]["precipitation_sum"].pop()
    with pytest.raises(weather.WeatherError, match="one value per day"):
        weather.parse_daily(payload)


def test_stops_on_a_value_that_cannot_be_right():
    payload = sample(ARCHIVE)
    payload["daily"]["sunshine_duration"][0] = 30 * 3600  # 30 hours of sun in one day
    with pytest.raises(weather.WeatherError, match="sunshine_hours on 2026-09-30 is 30.0"):
        weather.parse_daily(payload)


def test_stops_when_there_are_no_daily_values():
    with pytest.raises(weather.WeatherError, match="no daily values"):
        weather.parse_daily({"error": True})


# ---- asking the service -----------------------------------------------------------------------


def test_reports_the_reason_the_service_gives():
    session = FakeSession([FakeResponse(400, sample("open_meteo_error.json"))])
    with pytest.raises(weather.WeatherError, match="HTTP 400: Invalid value"):
        weather.fetch_json(session, weather.FORECAST_URL, {}, no_sleep)
    assert len(session.calls) == 1  # a wrong question is not asked again


def test_tries_again_when_the_service_is_busy():
    session = FakeSession([FakeResponse(503, "busy"), requests.ConnectionError("down"), FakeResponse(200, {"ok": 1})])
    assert weather.fetch_json(session, weather.FORECAST_URL, {}, no_sleep) == {"ok": 1}
    assert len(session.calls) == 3


def test_gives_up_after_three_tries():
    session = FakeSession([FakeResponse(503, "busy")] * 3)
    with pytest.raises(weather.WeatherError, match="HTTP 503"):
        weather.fetch_json(session, weather.FORECAST_URL, {}, no_sleep)


# ---- turning answers into rows ----------------------------------------------------------------


def rows_for(archive_payload, forecast_payload, today=TODAY, history_days=10):
    return weather.build_rows(
        SEEDED_RESTAURANT,
        today,
        today - timedelta(days=history_days),
        weather.parse_daily(archive_payload),
        weather.parse_daily(forecast_payload),
    )


def test_one_row_per_day_past_measured_future_forecast():
    rows = rows_for(sample(ARCHIVE), sample(FORECAST))
    assert [row["date"] for row in rows] == [(date(2026, 9, 30) + timedelta(days=n)).isoformat() for n in range(24)]
    assert [row["is_forecast"] for row in rows] == [False] * 10 + [True] * 14
    by_day = {row["date"]: row for row in rows}
    # 9 October: the archive measured 14.7, the forecast service said 14.0. Measured wins.
    assert by_day["2026-10-09"]["temp_max"] == 14.7
    assert by_day["2026-10-10"]["temp_max"] == 14.2
    assert set(rows[0]) == {"restaurant_id", "date", "temp_max", "rain_mm", "wind_max", "sunshine_hours", "is_forecast"}


def test_recent_days_missing_from_the_archive_come_from_the_forecast_service():
    archive = sample(ARCHIVE)
    for name in ("temperature_2m_max", "precipitation_sum", "wind_speed_10m_max", "sunshine_duration"):
        archive["daily"][name][-2:] = [None, None]  # the archive is two days behind
    by_day = {row["date"]: row for row in rows_for(archive, sample(FORECAST))}
    assert by_day["2026-10-08"]["temp_max"] == 16.7 and by_day["2026-10-08"]["is_forecast"] is False
    assert by_day["2026-10-09"]["temp_max"] == 14.0 and by_day["2026-10-09"]["is_forecast"] is False
    assert by_day["2026-10-07"]["temp_max"] == 21.8  # still the measured value


def test_stops_when_a_day_has_no_weather_at_all():
    forecast = sample(FORECAST)
    forecast["daily"]["temperature_2m_max"][-1] = None  # the last forecast day is missing
    with pytest.raises(weather.WeatherError, match=r"no weather for 1 day\(s\): 2026-10-23"):
        rows_for(sample(ARCHIVE), forecast)


def test_stops_when_history_is_asked_further_back_than_the_answers_reach():
    with pytest.raises(weather.WeatherError, match=r"no weather for 5 day\(s\): 2026-09-25"):
        rows_for(sample(ARCHIVE), sample(FORECAST), history_days=15)


# ---- writing to the database ------------------------------------------------------------------


def load(db, archive, forecast, today=TODAY, **options):
    session = session_with(archive, forecast)
    summaries = weather.load_all(db, session, today=today, history_days=10, sleep=no_sleep, **options)
    return summaries[0], session


def test_asks_for_the_right_place_and_period(db):
    _, session = load(db, sample(ARCHIVE), sample(FORECAST))
    archive_call, forecast_call = session.calls
    assert archive_call["url"] == weather.ARCHIVE_URL
    assert archive_call["params"] == {
        "latitude": 52.2066,
        "longitude": 6.8914,
        "timezone": "Europe/Amsterdam",
        "daily": "temperature_2m_max,precipitation_sum,wind_speed_10m_max,sunshine_duration",
        "start_date": "2026-09-30",
        "end_date": "2026-10-09",
    }
    assert forecast_call["url"] == weather.FORECAST_URL
    assert forecast_call["params"]["past_days"] == 10 and forecast_call["params"]["forecast_days"] == 14


def test_writes_history_and_forecast(db, owner):
    summary, _ = load(db, sample(ARCHIVE), sample(FORECAST))
    assert (summary.measured_days, summary.forecast_days) == (10, 14)
    assert (summary.rows_before, summary.rows_after) == (0, 24)
    assert (summary.first_day, summary.last_day) == (date(2026, 9, 30), date(2026, 10, 23))

    stored = owner.execute(
        "select date::text, temp_max::float, rain_mm::float, wind_max::float, sunshine_hours::float, is_forecast "
        "from public.daily_weather where restaurant_id = %s order by date",
        [SEEDED_RESTAURANT],
    ).fetchall()
    assert len(stored) == 24
    assert stored[0] == ("2026-09-30", 27.0, 0.0, 13.9, 10.3, False)
    assert stored[10] == ("2026-10-10", 14.2, 5.8, 25.9, 9.4, True)
    assert stored[-1][0] == "2026-10-23" and stored[-1][5] is True


def test_running_twice_adds_nothing(db, owner):
    load(db, sample(ARCHIVE), sample(FORECAST))
    before = owner.execute("select count(*), md5(string_agg(d::text, '|' order by d.date)) from public.daily_weather d").fetchone()

    summary, _ = load(db, sample(ARCHIVE), sample(FORECAST), expect_unchanged=True)

    after = owner.execute("select count(*), md5(string_agg(d::text, '|' order by d.date)) from public.daily_weather d").fetchone()
    assert (summary.rows_before, summary.rows_after) == (24, 24)
    assert after == before  # same number of rows and every row identical
    duplicates = owner.execute(
        "select count(*) from (select 1 from public.daily_weather group by restaurant_id, date having count(*) > 1) x"
    ).fetchone()[0]
    assert duplicates == 0


def test_the_next_day_updates_rows_instead_of_adding_copies(db, owner):
    load(db, sample(ARCHIVE), sample(FORECAST))
    archive, forecast = one_day_later(sample(ARCHIVE), sample(FORECAST))

    summary, _ = load(db, archive, forecast, today=TODAY + timedelta(days=1))

    assert (summary.rows_before, summary.rows_after) == (24, 25)  # exactly one new day: 24 October
    by_day = {
        row[0]: row[1:]
        for row in owner.execute("select date::text, temp_max::float, is_forecast from public.daily_weather").fetchall()
    }
    assert len(by_day) == 25
    assert by_day["2026-10-10"] == (15.5, False)  # was a 14.2 forecast, now the measured value
    assert by_day["2026-10-11"][1] is True
    assert by_day["2026-10-24"] == (13.0, True)
    assert by_day["2026-09-30"] == (27.0, False)  # older history is left as it was


def test_repeat_run_check_fails_if_rows_were_added(db):
    with pytest.raises(weather.WeatherError, match=r"added 24 row\(s\)"):
        load(db, sample(ARCHIVE), sample(FORECAST), expect_unchanged=True)  # first run on an empty table


def test_stops_if_an_old_day_is_still_marked_as_forecast(db, owner):
    owner.execute(
        "insert into public.daily_weather (restaurant_id, date, temp_max, rain_mm, is_forecast) values (%s, '2026-08-01', 20, 0, true)",
        [SEEDED_RESTAURANT],
    )
    with pytest.raises(weather.WeatherError, match=r"1 past day\(s\) are still marked as forecast"):
        load(db, sample(ARCHIVE), sample(FORECAST))


def test_writes_nothing_when_an_answer_is_bad(db, owner):
    forecast = sample(FORECAST)
    forecast["daily_units"]["temperature_2m_max"] = "°F"
    with pytest.raises(weather.WeatherError):
        load(db, sample(ARCHIVE), forecast)
    assert owner.execute("select count(*) from public.daily_weather").fetchone()[0] == 0


def test_stops_when_there_is_no_restaurant(db, owner):
    class NoRestaurants:
        def select(self, *args, **kwargs):
            return []

    with pytest.raises(weather.WeatherError, match="no restaurant"):
        weather.load_all(NoRestaurants(), FakeSession([]), today=TODAY, sleep=no_sleep)


def test_the_weather_job_cannot_touch_overrides(db):
    """The rights in the migration, seen from the job's side: overrides are read-only."""
    import psycopg

    assert db.count("forecast_overrides") == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.upsert(
            "forecast_overrides",
            [{"restaurant_id": SEEDED_RESTAURANT, "date": "2026-10-10", "shift": "dinner", "servers": 1, "cooks": 1}],
            on_conflict=["restaurant_id", "date", "shift"],
        )
