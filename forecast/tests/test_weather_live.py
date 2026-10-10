"""Asks the real weather service for the full two years. Needs the internet, so it is skipped
unless LIVE_WEATHER=1 is set. It touches no database and needs no keys.

    LIVE_WEATHER=1 python -m pytest forecast/tests/test_weather_live.py -q -s
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import requests

from forecast import report, weather
from forecast.tests.test_weather import RESTAURANT

pytestmark = pytest.mark.skipif(
    os.environ.get("LIVE_WEATHER") != "1", reason="set LIVE_WEATHER=1 to ask the real weather service"
)


def test_the_real_service_gives_two_years_of_history_and_fourteen_days_of_forecast():
    today = datetime.now(ZoneInfo(RESTAURANT["timezone"])).date()

    rows = weather.fetch_rows(requests.Session(), RESTAURANT, today=today, history_days=731)

    assert len(rows) == 731 + 14
    assert rows[0]["date"] == (today - timedelta(days=731)).isoformat()
    assert rows[-1]["date"] == (today + timedelta(days=13)).isoformat()
    assert [row["is_forecast"] for row in rows] == [False] * 731 + [True] * 14
    assert len({row["date"] for row in rows}) == len(rows)

    no_wind = sum(row["wind_max"] is None for row in rows)
    no_sun = sum(row["sunshine_hours"] is None for row in rows)
    warmest = max(rows, key=lambda row: row["temp_max"])
    wettest = max(rows, key=lambda row: row["rain_mm"])
    report.result(
        "Real weather service",
        f"{len(rows)} days, {rows[0]['date']} to {rows[-1]['date']}: 731 measured, 14 forecast, no day missing. "
        f"Days without a wind value: {no_wind}, without a sunshine value: {no_sun}. "
        f"Warmest day {warmest['date']} ({warmest['temp_max']} °C), wettest day {wettest['date']} ({wettest['rain_mm']} mm).",
    )
