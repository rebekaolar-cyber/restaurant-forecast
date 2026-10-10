"""Tests for the fake booking system, run on the real weather saved from the database."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo

import pytest

from forecast import fake_history as fh
from forecast.calendar_nl import is_ordinary
from forecast.history import parse_moment, service_date
from forecast.manager_plan import REAL_FRIDAY_GUESTS, REAL_FRIDAY_RESERVATIONS
from forecast.tests.conftest import HABIBI, SEEDED_RESTAURANT, measured_weather, put_weather

TZ = ZoneInfo("Europe/Amsterdam")
AS_OF = datetime(2026, 10, 10, 3, 0, tzinfo=TZ)      # the night after Friday 9 October 2026
TODAY = date(2026, 10, 10)
MILD = {"temp_max": 14.0, "rain_mm": 0.0, "wind_max": 15.0}
WET = {"temp_max": 14.0, "rain_mm": 18.0, "wind_max": 15.0}
WARM = {"temp_max": 27.0, "rain_mm": 0.0, "wind_max": 10.0}


@pytest.fixture(scope="module")
def two_years():
    """The whole fake history, generated once for this file."""
    weather = measured_weather()
    bookings, receipts = fh.generate(HABIBI, weather, first_day=min(weather), as_of=AS_OF)
    return bookings, receipts


def per_evening(bookings, receipts):
    book = defaultdict(lambda: {"parties": 0, "guests": 0})
    for row in bookings:
        day = date.fromisoformat(row["visit_date"])
        if day < TODAY and row["status"] != "cancelled":
            book[day]["parties"] += 1
            book[day]["guests"] += row["party_size"]
    served = defaultdict(int)
    for row in receipts:
        served[service_date(parse_moment(row["opened_at"]), TZ)] += row["guests"]
    return book, served


# ---- what the rows look like -------------------------------------------------------------------


def test_the_same_evening_always_comes_out_the_same(two_years):
    weather = measured_weather()
    again = fh.generate(HABIBI, weather, first_day=min(weather), as_of=AS_OF)
    assert again == two_years


def test_rows_hold_only_the_contract_columns_and_nothing_personal(two_years):
    bookings, receipts = two_years
    assert set(bookings[0]) == {"id", "restaurant_id", "visit_date", "visit_time", "party_size", "table_no", "created_at", "status"}
    assert set(receipts[0]) == {"id", "restaurant_id", "opened_at", "closed_at", "table_no", "guests", "total"}
    assert {row["status"] for row in bookings} == {"booked", "completed", "no_show", "cancelled"}
    assert len({row["id"] for row in bookings}) == len(bookings)
    assert len({row["id"] for row in receipts}) == len(receipts)
    assert {row["restaurant_id"] for row in bookings + receipts} == {SEEDED_RESTAURANT}


def test_two_years_of_evenings_every_one_with_guests(two_years):
    book, served = per_evening(*two_years)
    assert min(served) == date(2024, 10, 9) and max(served) == date(2026, 10, 9)
    assert len(served) == 731 and min(served.values()) > 0


# ---- how busy ---------------------------------------------------------------------------------


def test_a_normal_friday_lands_on_the_real_number(two_years):
    """The restaurant's book on Friday 9 October 2026: 47 reservations, 174 people, walk-ins included."""
    book, _ = per_evening(*two_years)
    fridays = [day for day in book if day.weekday() == 4 and is_ordinary(day) and day.month != 1]
    assert len(fridays) > 80
    assert mean(book[day]["parties"] for day in fridays) == pytest.approx(REAL_FRIDAY_RESERVATIONS, abs=2)
    assert mean(book[day]["guests"] for day in fridays) == pytest.approx(REAL_FRIDAY_GUESTS, abs=5)
    # And that very Friday in the fake book:
    assert book[date(2026, 10, 9)]["parties"] == pytest.approx(REAL_FRIDAY_RESERVATIONS, abs=6)
    assert book[date(2026, 10, 9)]["guests"] == pytest.approx(REAL_FRIDAY_GUESTS, abs=25)


def test_friday_and_saturday_are_the_busy_evenings(two_years):
    _, served = per_evening(*two_years)
    by_weekday = [mean(v for day, v in served.items() if day.weekday() == weekday) for weekday in range(7)]
    monday, _, _, thursday, friday, saturday, sunday = by_weekday
    assert saturday > friday > sunday > thursday > monday
    assert friday > 2 * monday


def test_january_is_quiet(two_years):
    _, served = per_evening(*two_years)
    january = mean(v for day, v in served.items() if day.month == 1 and day.day > 1)
    rest = mean(v for day, v in served.items() if day.month != 1)
    assert january < 0.8 * rest


def test_public_holidays_are_busier_than_the_same_weekday(two_years):
    _, served = per_evening(*two_years)
    ordinary_monday = mean(v for day, v in served.items() if day.weekday() == 0 and is_ordinary(day) and day.month != 1)
    assert served[date(2025, 4, 21)] > 1.3 * ordinary_monday    # Easter Monday
    assert served[date(2026, 5, 25)] > 1.3 * ordinary_monday    # Whit Monday
    assert served[date(2025, 12, 25)] > 1.5 * mean(
        v for day, v in served.items() if day.weekday() == 3 and is_ordinary(day) and day.month != 1
    )  # Christmas Day 2025 was a Thursday


def test_rain_keeps_walk_ins_away_and_a_warm_dry_evening_brings_them():
    day = date(2026, 9, 16)  # an ordinary Wednesday
    reserved = fh.reserved_parties(HABIBI, day)
    guests = lambda weather: sum(p.size for p in fh.walk_in_parties(HABIBI, day, weather, reserved))  # noqa: E731
    assert guests(WET) < guests(MILD) < guests(WARM)
    assert fh.walk_in_weather_factor(WET) == 0.60
    assert fh.walk_in_weather_factor(MILD) == 1.0
    assert fh.walk_in_weather_factor(WARM) == 1.45
    assert fh.walk_in_weather_factor({"temp_max": 27.0, "rain_mm": 6.0, "wind_max": None}) == 0.72  # warm but wet: no terrace


def test_reservations_do_not_depend_on_the_weather():
    """So the book for an evening to come never changes when the weather forecast does."""
    day = date(2026, 10, 16)
    dry, _ = fh.rows_for_day(HABIBI, day, as_of=AS_OF, weather=None)
    wet, _ = fh.rows_for_day(HABIBI, day, as_of=AS_OF, weather=WET)
    assert dry == wet and len(dry) > 0


def test_never_more_guests_than_the_restaurant_can_seat(two_years):
    _, served = per_evening(*two_years)
    assert max(served.values()) <= round(254 * fh.CAPACITY_TURNS) + 5


# ---- bookings: how far ahead, no-shows, cancellations ----------------------------------------


def test_bookings_are_made_0_to_30_days_ahead_and_before_arrival():
    for offset in range(0, 60, 3):
        day = date(2026, 6, 1) + timedelta(days=offset)
        for party in fh.reserved_parties(HABIBI, day):
            ahead = (day - party.created_at.astimezone(TZ).date()).days
            assert 0 <= ahead <= 30
            arrival = datetime.combine(day, datetime.min.time(), tzinfo=TZ) + timedelta(minutes=party.visit_minutes)
            assert party.created_at < arrival


def test_about_five_percent_no_shows_and_a_few_cancellations():
    outcomes = defaultdict(int)
    for offset in range(365):
        for party in fh.reserved_parties(HABIBI, date(2025, 10, 1) + timedelta(days=offset)):
            outcomes[party.outcome] += 1
    kept = outcomes["completed"] + outcomes["no_show"]
    assert outcomes["no_show"] / kept == pytest.approx(0.05, abs=0.01)
    assert outcomes["cancelled"] / kept == pytest.approx(0.03, abs=0.01)


def test_weekends_are_booked_earlier_than_weekdays():
    def booked_a_week_ahead(weekday):
        parties = [
            p
            for offset in range(0, 364)
            if (day := date(2025, 10, 1) + timedelta(days=offset)).weekday() == weekday
            for p in fh.reserved_parties(HABIBI, day)
            if (day - p.created_at.astimezone(TZ).date()).days >= 7
        ]
        everyone = sum(len(fh.reserved_parties(HABIBI, date(2025, 10, 1) + timedelta(days=o))) for o in range(0, 364) if (date(2025, 10, 1) + timedelta(days=o)).weekday() == weekday)
        return len(parties) / everyone

    assert booked_a_week_ahead(5) > booked_a_week_ahead(1) + 0.1   # Saturday against Tuesday


def test_walk_ins_are_in_the_book_from_the_moment_they_arrive():
    day = date(2026, 9, 18)
    walk_ins = fh.walk_in_parties(HABIBI, day, MILD, fh.reserved_parties(HABIBI, day))
    assert walk_ins and all(p.kind == "walk_in" and p.outcome == "completed" for p in walk_ins)
    for p in walk_ins:
        assert p.created_at.astimezone(TZ).date() == day
        assert p.created_at.astimezone(TZ).hour * 60 + p.created_at.astimezone(TZ).minute == p.visit_minutes


def test_guests_arrive_during_opening_hours(two_years):
    bookings, _ = two_years
    for row in bookings[:: 37]:
        weekday = date.fromisoformat(row["visit_date"]).weekday()
        earliest = "16:00:00" if weekday == 6 else "17:00:00"
        latest = "22:00:00" if weekday in (4, 5) else "20:30:00" if weekday == 6 else "21:00:00"
        assert earliest <= row["visit_time"] <= latest


def test_a_late_table_on_saturday_still_belongs_to_saturday(two_years):
    _, receipts = two_years
    past_midnight = [
        row for row in receipts
        if parse_moment(row["closed_at"]).astimezone(TZ).date() > parse_moment(row["opened_at"]).astimezone(TZ).date()
    ]
    assert past_midnight, "some Friday and Saturday tables should close after midnight"
    for row in past_midnight:
        opened = parse_moment(row["opened_at"])
        assert service_date(opened, TZ).weekday() in (4, 5)   # only Friday and Saturday are open that late
        assert service_date(parse_moment(row["closed_at"]), TZ) == service_date(opened, TZ)


def test_every_table_is_closed_by_a_quarter_past_closing_time(two_years):
    _, receipts = two_years
    for row in receipts:
        opened, closed = parse_moment(row["opened_at"]).astimezone(TZ), parse_moment(row["closed_at"]).astimezone(TZ)
        evening = service_date(opened, TZ)
        closing = datetime.combine(evening, datetime.min.time(), tzinfo=TZ) + timedelta(
            hours=25 if evening.weekday() in (4, 5) else 23, minutes=15
        )
        assert opened < closed <= closing


# ---- the book for evenings to come ------------------------------------------------------------


def test_an_evening_to_come_shows_only_the_bookings_made_so_far():
    day = date(2026, 10, 17)   # a Saturday, a week after "now"
    now, receipts_now = fh.rows_for_day(HABIBI, day, as_of=AS_OF, weather=None)
    later, _ = fh.rows_for_day(HABIBI, day, as_of=AS_OF + timedelta(days=5), weather=None)
    assert receipts_now == []
    assert {row["status"] for row in now} <= {"booked", "cancelled"}
    assert all(parse_moment(row["created_at"]) <= AS_OF for row in now)
    assert 0 < len(now) < len(later)
    assert {row["id"] for row in now} < {row["id"] for row in later}   # the book only grows


def test_an_evening_that_is_over_needs_its_measured_weather():
    with pytest.raises(fh.FakeHistoryError, match="no measured weather for 2026-10-09"):
        fh.rows_for_day(HABIBI, date(2026, 10, 9), as_of=AS_OF, weather=None)


def test_as_of_needs_a_timezone():
    with pytest.raises(fh.FakeHistoryError, match="needs a timezone"):
        fh.parse_as_of("2026-10-10T03:00:00")
    assert fh.parse_as_of("2026-10-10T03:00:00+02:00") == AS_OF


# ---- in the database --------------------------------------------------------------------------

FIRST_DAY = date(2026, 6, 1)   # the database tests use the last four months, to stay quick


def snapshot(owner, before: date):
    """A fingerprint of every booking and receipt for evenings before a day."""
    return owner.execute(
        "select (select md5(coalesce(string_agg(b::text, '|' order by b.id), '')) from public.bookings b where visit_date < %s), "
        "(select md5(coalesce(string_agg(r::text, '|' order by r.id), '')) from public.receipts r where opened_at < %s::date + interval '4 hours')",
        [before, before],
    ).fetchone()


def test_fills_the_database_and_a_repeat_run_adds_nothing(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 10, 23))

    first = fh.top_up_all(db, as_of=AS_OF)[0]
    assert (first.evenings_closed, first.first_closed, first.last_closed) == (131, FIRST_DAY, date(2026, 10, 9))
    assert first.bookings_before == 0 and first.bookings_after > 3000
    assert first.receipts_before == 0 and first.receipts_after > 3000

    again = fh.top_up_all(db, as_of=AS_OF, expect_unchanged=True)[0]
    assert again.evenings_closed == 0
    assert (again.bookings_after, again.receipts_after) == (first.bookings_after, first.receipts_after)

    # The database holds exactly what the generator makes.
    bookings, receipts = fh.generate(HABIBI, measured_weather(), first_day=FIRST_DAY, as_of=AS_OF)
    assert owner.execute("select count(*), sum(party_size) from public.bookings").fetchone() == (len(bookings), sum(b["party_size"] for b in bookings))
    assert owner.execute("select count(*), sum(guests), sum(total)::float from public.receipts").fetchone() == pytest.approx(
        (len(receipts), sum(r["guests"] for r in receipts), sum(r["total"] for r in receipts))
    )
    statuses = dict(owner.execute("select status, count(*) from public.bookings where visit_date >= %s group by 1", [TODAY]).fetchall())
    assert set(statuses) <= {"booked", "cancelled"} and statuses["booked"] > 50
    assert owner.execute("select count(*) from public.receipts where opened_at >= %s", [AS_OF]).fetchone()[0] == 0


def test_the_next_night_closes_yesterday_and_leaves_older_evenings_alone(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 10, 23))
    first = fh.top_up_all(db, as_of=AS_OF)[0]
    older = snapshot(owner, TODAY)
    booked_for_today = owner.execute("select count(*) from public.bookings where visit_date = %s", [TODAY]).fetchone()[0]

    # A day passes: Saturday 10 October now has measured weather.
    put_weather(owner, TODAY, TODAY, measured_through=TODAY)
    second = fh.top_up_all(db, as_of=AS_OF + timedelta(days=1))[0]

    assert (second.evenings_closed, second.first_closed, second.last_closed) == (1, TODAY, TODAY)
    assert second.receipts_after > first.receipts_after
    assert second.bookings_after > first.bookings_after
    assert snapshot(owner, TODAY) == older   # nothing before Saturday changed
    saturday = dict(owner.execute("select status, count(*) from public.bookings where visit_date = %s group by 1", [TODAY]).fetchall())
    assert "booked" not in saturday and saturday["completed"] > booked_for_today   # walk-ins joined the book
    assert owner.execute(
        "select count(*) from public.receipts where opened_at >= %s and opened_at < %s", [AS_OF, AS_OF + timedelta(days=1)]
    ).fetchone()[0] == saturday["completed"]


def test_a_closed_evening_never_changes_even_if_its_weather_is_revised(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 10, 23))
    fh.top_up_all(db, as_of=AS_OF)
    before = snapshot(owner, TODAY)

    owner.execute("update public.daily_weather set rain_mm = 40, temp_max = 2 where date < %s", [TODAY])
    fh.top_up_all(db, as_of=AS_OF, expect_unchanged=True)

    assert snapshot(owner, TODAY) == before


def test_rebuild_deletes_and_makes_the_same_rows_again(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 10, 23))
    fh.top_up_all(db, as_of=AS_OF)
    before = snapshot(owner, date(2027, 1, 1))
    owner.execute("update public.bookings set party_size = 99 where visit_date = '2026-09-01'")

    fh.top_up_all(db, as_of=AS_OF, rebuild=True)

    assert snapshot(owner, date(2027, 1, 1)) == before


def test_stops_when_yesterdays_weather_is_missing(db, owner):
    put_weather(owner, FIRST_DAY, date(2026, 10, 7))   # 8 and 9 October were never loaded
    with pytest.raises(fh.FakeHistoryError, match="no measured weather for 2026-10-08"):
        fh.top_up_all(db, as_of=AS_OF)
    assert owner.execute("select count(*) from public.bookings").fetchone()[0] == 0


def test_stops_when_there_is_no_weather_at_all(db):
    with pytest.raises(fh.FakeHistoryError, match="load the weather first"):
        fh.top_up_all(db, as_of=AS_OF)
