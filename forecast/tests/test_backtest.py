"""Tests for the backtest: is the scoring right, and is the saved report still true?"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from forecast import backtest as bt
from forecast import fake_history as fh
from forecast.baseline import ForecastError
from forecast.history import History
from forecast.manager_plan import GUESTS_BY_WEEKDAY
from forecast.tests.conftest import HABIBI, REPO, WEATHER_CSV, measured_weather, put_weather

TZ = ZoneInfo("Europe/Amsterdam")
AS_OF = datetime(2026, 10, 10, 3, 0, tzinfo=TZ)
LAST_DAY = date(2026, 10, 9)
REPORTS = REPO / "forecast" / "reports"


def steady_history(share_of_plan: float) -> History:
    """A restaurant where every evening has exactly this share of the manager's plan, and no bookings."""
    guests = {}
    for back in range(200):
        day = LAST_DAY - timedelta(days=back)
        guests[day] = round(GUESTS_BY_WEEKDAY[day.weekday()] * share_of_plan)
    return History(TZ, guests, [])


def test_a_perfectly_regular_restaurant_is_forecast_exactly():
    result = bt.run_backtest(steady_history(0.5), bt.OFFLINE_BANDS, last_day=LAST_DAY, days=28)
    assert result["evenings"] == 28
    assert (result["first_evening"], result["last_evening"]) == ("2026-09-12", "2026-10-09")
    for days_ahead in ("1", "3", "7", "14"):
        scores = result["horizons"][days_ahead]
        assert scores["forecast"] == {"average_error": 0.0, "leaning": 0.0}
        assert scores["weekday_average"] == {"average_error": 0.0, "leaning": 0.0}
        # The plan is twice the real guests every evening: off by the real guests, always too high.
        assert scores["manager_plan"]["average_error"] == scores["manager_plan"]["leaning"] == result["average_guests"]
        assert scores["evenings_forecast_closer_than_plan"] == 28
    assert bt.beats_the_plan(result)


def test_when_the_plan_is_right_the_forecast_does_not_beat_it():
    result = bt.run_backtest(steady_history(1.0), bt.OFFLINE_BANDS, last_day=LAST_DAY, days=28)
    assert result["horizons"]["1"]["manager_plan"]["average_error"] == 0.0
    assert result["horizons"]["1"]["evenings_forecast_closer_than_plan"] == 0
    assert not bt.beats_the_plan(result)
    assert "does NOT beat" in bt.markdown_report(result, source="test")


def test_roster_comparison_uses_the_managers_table():
    # Real guests are half the plan: Friday 125 (row 120: 11 staff), the plan says 250 (16 staff).
    result = bt.run_backtest(steady_history(0.5), bt.OFFLINE_BANDS, last_day=LAST_DAY, days=7)
    staff = result["horizons"]["7"]["staffing"]
    assert staff["forecast_right"] == 7 and staff["forecast_extra"] == 0 and staff["forecast_short"] == 0
    # Mon-Wed 50 -> 7 staff, plan 100 -> 7. Thu 60 -> 7, plan 120 -> 11. Fri 125 -> 11, plan 250 -> 16.
    # Sat 150 -> 11, plan 300 -> 16. Sun 90 -> 7, plan 180 -> 14.
    assert staff["plan_right"] == 3
    assert staff["plan_extra"] == 4 + 5 + 5 + 7 and staff["plan_short"] == 0


def test_plan_scale_is_the_real_friday_over_the_planned_friday():
    assert bt.PLAN_SCALE == pytest.approx(174 / 250)


def test_stops_when_an_evening_in_the_period_has_no_receipts():
    history = steady_history(0.5)
    del history._guests[date(2026, 10, 1)]
    with pytest.raises(ForecastError, match="no receipts for 1 evening"):
        bt.run_backtest(history, bt.OFFLINE_BANDS, last_day=LAST_DAY, days=28)


def test_the_saved_report_is_what_the_code_produces_today():
    """forecast/reports/ must never go stale: it has to equal a fresh run on the saved weather."""
    history = bt.offline_history(WEATHER_CSV, AS_OF)
    result = bt.run_backtest(history, bt.OFFLINE_BANDS, last_day=LAST_DAY)
    saved = json.loads((REPORTS / "baseline_backtest.json").read_text(encoding="utf-8"))
    assert {key: saved[key] for key in result} == result
    assert saved["first_evening"] == "2026-07-10" and saved["last_evening"] == "2026-10-09"
    # 92 evenings, minus 4 closed Mondays before 10 August and 4 Mondays with too few earlier Mondays.
    assert (saved["evenings"], saved["evenings_closed"], saved["evenings_too_new"]) == (84, 4, 4)
    text = (REPORTS / "baseline_backtest.md").read_text(encoding="utf-8")
    for days_ahead, scores in result["horizons"].items():
        assert f"| {days_ahead} | {scores['forecast']['average_error']} | {scores['weekday_average']['average_error']} |" in text
    assert "This is fake history" in text


def test_the_report_tells_the_whole_story():
    history = bt.offline_history(WEATHER_CSV, AS_OF)
    result = bt.run_backtest(history, bt.OFFLINE_BANDS, last_day=LAST_DAY)
    # On this fake history the plan is far off, by construction, and the forecast beats it.
    assert bt.beats_the_plan(result)
    for scores in result["horizons"].values():
        assert scores["manager_plan"]["average_error"] > 3 * scores["forecast"]["average_error"]
        assert scores["manager_plan"]["leaning"] > 0          # the plan is always too high here
    # The forecast is better the closer the evening is.
    errors = [result["horizons"][n]["forecast"]["average_error"] for n in ("1", "3", "7", "14")]
    assert errors == sorted(errors)


def test_the_command_line_writes_both_report_files(tmp_path, capsys):
    code = bt.main(["--offline", str(WEATHER_CSV), "--as-of", "2026-10-10T03:00:00+02:00", "--report-dir", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "baseline_backtest.md").read_text(encoding="utf-8") == (REPORTS / "baseline_backtest.md").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "baseline_backtest.json").read_text()) == json.loads((REPORTS / "baseline_backtest.json").read_text())
    assert "our forecast beats the manager's plan at every distance (fake history)" in capsys.readouterr().out


def test_the_backtest_from_the_database_equals_the_one_from_memory(db, owner):
    first_day = date(2026, 3, 1)
    put_weather(owner, first_day, date(2026, 10, 23))
    fh.top_up_all(db, as_of=AS_OF)

    from_database = bt.run_backtest(bt.database_history(db, HABIBI, LAST_DAY), bt.OFFLINE_BANDS, last_day=LAST_DAY, days=60)

    bookings, receipts = fh.generate(HABIBI, measured_weather(), first_day=first_day, as_of=AS_OF)
    from_memory = bt.run_backtest(History.from_rows(TZ, bookings, receipts), bt.OFFLINE_BANDS, last_day=LAST_DAY, days=60)
    assert from_database == from_memory
