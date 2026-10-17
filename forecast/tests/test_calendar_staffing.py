"""Tests for the Dutch calendar, the staffing table and the manager's plan."""

from __future__ import annotations

from datetime import date

import pytest

from forecast import staffing
from forecast.backtest import OFFLINE_BANDS, OFFLINE_RESTAURANT
from forecast.calendar_nl import easter_sunday, holiday_name, is_ordinary, public_holidays, special_name
from forecast.manager_plan import planned_guests
from forecast.tests.conftest import HABIBI, SEEDED_RESTAURANT

BANDS = OFFLINE_BANDS


def test_easter_is_calculated_correctly():
    assert easter_sunday(2024) == date(2024, 3, 31)
    assert easter_sunday(2025) == date(2025, 4, 20)
    assert easter_sunday(2026) == date(2026, 4, 5)
    assert easter_sunday(2027) == date(2027, 3, 28)


def test_dutch_public_holidays_of_2025_and_2026():
    assert public_holidays(2025) == {
        date(2025, 1, 1): "new_years_day",
        date(2025, 4, 18): "good_friday",
        date(2025, 4, 20): "easter_sunday",
        date(2025, 4, 21): "easter_monday",
        date(2025, 4, 26): "kings_day",        # 27 April 2025 is a Sunday, so it moves a day
        date(2025, 5, 5): "liberation_day",
        date(2025, 5, 29): "ascension_day",
        date(2025, 6, 8): "whit_sunday",
        date(2025, 6, 9): "whit_monday",
        date(2025, 12, 25): "christmas_day",
        date(2025, 12, 26): "boxing_day",
    }
    assert holiday_name(date(2026, 4, 27)) == "kings_day"
    assert holiday_name(date(2026, 5, 14)) == "ascension_day"
    assert holiday_name(date(2026, 5, 25)) == "whit_monday"
    assert holiday_name(date(2026, 10, 9)) is None


def test_special_evenings():
    assert special_name(date(2026, 2, 14)) == "valentines_day"
    assert special_name(date(2026, 5, 10)) == "mothers_day"   # second Sunday of May
    assert special_name(date(2025, 12, 31)) == "new_years_eve"
    assert is_ordinary(date(2026, 10, 9)) and not is_ordinary(date(2026, 12, 25))


def test_the_managers_weekly_plan():
    # 5 to 11 October 2026 is Monday to Sunday.
    assert [planned_guests(date(2026, 10, day)) for day in range(5, 12)] == [100, 100, 100, 120, 250, 300, 180]


# ---- the staffing table -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "guests, roster",
    [
        (0, "3W 1B 1R 2F + 4 kitchen"),      # below the first row: still the smallest roster
        (99, "3W 1B 1R 2F + 4 kitchen"),
        (100, "3W 1B 1R 2F + 4 kitchen"),
        (119, "3W 1B 1R 2F + 4 kitchen"),
        (120, "4W 2B 2R 3F + 4 kitchen"),    # a row applies from its guest number
        (174, "4W 2B 2R 3F + 4 kitchen"),    # the real Friday
        (179, "4W 2B 2R 3F + 4 kitchen"),
        (180, "6W 3B 2R 3F + 4 kitchen"),
        (249, "6W 3B 2R 3F + 4 kitchen"),
        (250, "6W 3B 3R 4F + 4 kitchen"),
        (300, "6W 3B 3R 4F + 4 kitchen"),
        (450, "6W 3B 3R 4F + 4 kitchen"),    # above the last row: the largest roster
    ],
)
def test_guests_become_staff_by_the_managers_table(guests, roster):
    assert staffing.roster_text(staffing.staff_for(guests, BANDS)) == roster


def test_the_order_of_the_rows_does_not_matter():
    assert staffing.staff_for(130, list(reversed(BANDS))) == staffing.staff_for(130, BANDS)


def test_kitchen_is_the_fixed_four_whatever_the_guests():
    assert {staffing.staff_for(guests, BANDS)["cooks"] for guests in range(0, 400, 10)} == {4}


def test_staffing_refuses_nonsense():
    with pytest.raises(staffing.StaffingError, match="empty"):
        staffing.staff_for(100, [])
    with pytest.raises(staffing.StaffingError, match="negative"):
        staffing.staff_for(-1, BANDS)


def test_the_table_in_the_database_is_the_managers_table(db):
    assert staffing.load_bands(db, SEEDED_RESTAURANT) == BANDS


def test_an_empty_table_in_the_database_stops_the_job(db):
    with pytest.raises(staffing.StaffingError, match="empty"):
        staffing.load_bands(db, "00000000-0000-0000-0000-000000000000")


def test_the_offline_restaurant_matches_the_seed(db):
    stored = db.select("restaurants", "id,name,timezone,seats", order="name")
    assert stored == [OFFLINE_RESTAURANT]
    assert {key: HABIBI[key] for key in OFFLINE_RESTAURANT} == OFFLINE_RESTAURANT


def test_mondays_open_only_from_10_august_2026():
    from forecast.opening import is_open

    assert not is_open(date(2026, 8, 3)) and is_open(date(2026, 8, 10)) and is_open(date(2026, 10, 12))
    assert all(is_open(date(2025, 6, day)) for day in (3, 4, 5, 6, 7, 8))   # Tuesday to Sunday
    assert not is_open(date(2025, 6, 2))                                    # a Monday in 2025
