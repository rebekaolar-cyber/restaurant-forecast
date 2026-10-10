"""A fake booking system and till, so the forecast has something to learn from before real data.

It fills `bookings` and `receipts` with made-up evenings that follow the real weather:

- busier on Friday and Saturday, quiet weeks in January, public holidays
- closed on Mondays before 10 August 2026, as the real restaurant was
- fewer walk-ins on rainy days, more on warm dry evenings (the terrace effect)
- bookings made 0 to 30 days ahead, about 5% no-shows
- no names, phone numbers or emails: a party is a time, a size and a table

How busy? The weekday shape is the manager's own plan. The level comes from the one real number
we have: on Friday 9 October 2026 the reservation book held 47 reservations for 174 people,
walk-ins included, where his plan says 250. So every weekday is set to his plan times 174/250.
That is an assumption, not a measurement.

The reservation book includes walk-ins, as the restaurant's own book does: a walk-in is a
booking made at the moment the party arrives.

Everything is decided by a fixed seed and the date, so the same evening always comes out the
same. Running it again adds nothing. Running it a day later adds what "happened" since: new
bookings for the coming 30 days, and yesterday's walk-ins, no-shows and receipts. An evening
that has receipts is never changed again.

    python -m forecast.fake_history                      bring the fake book up to now
    python -m forecast.fake_history --as-of 2026-10-10T03:00:00+02:00
    python -m forecast.fake_history --expect-unchanged   also fail if this run added rows
    python -m forecast.fake_history --rebuild            delete the restaurant's bookings and
                                                         receipts first. FAKE DATA ONLY.

Remove this module from the nightly job before real bookings are imported.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from forecast import report
from forecast.calendar_nl import holiday_name, special_name
from forecast.db import Database, DatabaseError, RestDatabase
from forecast.history import parse_moment, service_date
from forecast.opening import is_open
from forecast.manager_plan import GUESTS_BY_WEEKDAY, REAL_FRIDAY_GUESTS
from forecast.settings import SettingsError, load_settings

SEED = 20261010
NAMESPACE = uuid.UUID("6f1c2a5e-3b7d-4c1e-9a52-0d8e4f7b2c10")
MAX_LEAD_DAYS = 30

# ---- how busy ---------------------------------------------------------------------------------

# The manager's weekday plan, scaled so that a normal Friday lands on the real 174 guests.
LEVEL = REAL_FRIDAY_GUESTS / GUESTS_BY_WEEKDAY[4]
# Fine-tuning so that ordinary Fridays over the two years average 174 guests in the book.
CALIBRATION = 1.02
# Share of an evening's guests that reserved ahead; the rest walk in. Monday = 0.
RESERVED_SHARE = {0: 0.55, 1: 0.55, 2: 0.55, 3: 0.58, 4: 0.70, 5: 0.72, 6: 0.62}
# What the weather does to walk-ins on an average day, so that it averages out to 1.
WEATHER_NEUTRAL = 0.99
# A day cannot seat more than this many times its seats (tables turn over once, partly).
CAPACITY_TURNS = 1.3

NO_SHOW_RATE = 0.05
CANCELLED_RATE = 0.03

MONTH_FACTOR = {2: 0.93, 3: 0.98, 4: 1.00, 5: 1.03, 6: 1.03, 7: 0.95, 8: 0.95, 9: 1.02, 10: 1.00, 11: 1.00}

# Public holidays when most people are off: at least as busy as a Sunday, times this.
DAY_OFF_HOLIDAYS = {
    "easter_sunday": 1.30,
    "easter_monday": 1.10,
    "kings_day": 1.20,
    "ascension_day": 1.10,
    "whit_sunday": 1.25,
    "whit_monday": 1.10,
    "christmas_day": 1.50,
    "boxing_day": 1.50,
}
# Other days that move the needle: the ordinary level of that weekday, times this.
OTHER_DAYS = {
    "new_years_day": 0.60,
    "good_friday": 1.10,
    "liberation_day": 1.10,
    "valentines_day": 1.45,
    "mothers_day": 1.40,
    "sinterklaas": 0.75,
    "christmas_eve": 0.85,
    "new_years_eve": 1.10,
}

# ---- who comes, when they book, when they arrive ---------------------------------------------

RESERVED_SIZES = {2: 0.33, 3: 0.12, 4: 0.23, 5: 0.08, 6: 0.10, 7: 0.02, 8: 0.05, 10: 0.035, 12: 0.02, 15: 0.01, 20: 0.005}
WALK_IN_SIZES = {1: 0.04, 2: 0.52, 3: 0.16, 4: 0.20, 5: 0.05, 6: 0.03}


def _lead_weights(first_week: list[float], week_two: float, week_three: float, later: float) -> list[float]:
    """Chance of booking 0, 1, 2 ... 30 days ahead."""
    return first_week + [week_two / 7] * 7 + [week_three / 7] * 7 + [later / 9] * 9


# Weekend evenings are booked earlier than weekday evenings.
LEAD_WEEKEND = _lead_weights([0.14, 0.12, 0.10, 0.09, 0.07, 0.06, 0.05, 0.05], 0.19, 0.08, 0.05)
LEAD_WEEKDAY = _lead_weights([0.28, 0.17, 0.12, 0.09, 0.06, 0.05, 0.04, 0.04], 0.10, 0.035, 0.015)


def _arrival_slots(first: time, last: time, busiest: time) -> tuple[list[int], list[float]]:
    """Quarter-hour arrival times in minutes after midnight, with the rush around `busiest`."""
    to_minutes = lambda t: t.hour * 60 + t.minute  # noqa: E731
    slots = list(range(to_minutes(first), to_minutes(last) + 1, 15))
    weights = [max(0.15, 1 - abs(slot - to_minutes(busiest)) / 150) for slot in slots]
    return slots, weights


# Opening hours: Mon-Thu 17:00-23:00, Fri-Sat 17:00-01:00, Sun 16:00-23:00.
CLOSING_MINUTES = {0: 23 * 60, 1: 23 * 60, 2: 23 * 60, 3: 23 * 60, 4: 25 * 60, 5: 25 * 60, 6: 23 * 60}
ARRIVALS_WEEKDAY = _arrival_slots(time(17, 0), time(21, 0), time(19, 0))
ARRIVALS_WEEKEND = _arrival_slots(time(17, 0), time(22, 0), time(19, 15))
ARRIVALS_SUNDAY = _arrival_slots(time(16, 0), time(20, 30), time(18, 15))


class FakeHistoryError(RuntimeError):
    """The fake booking system cannot do its work, for example because weather is missing."""


@dataclass(frozen=True)
class Party:
    booking_id: str
    kind: str            # "reserved" or "walk_in"
    size: int
    visit_minutes: int   # arrival, in minutes after midnight, local time
    created_at: datetime
    table_no: str
    outcome: str         # "completed", "no_show" or "cancelled"
    opened_at: datetime
    closed_at: datetime
    guests: int
    total: float


@dataclass(frozen=True)
class FeedSummary:
    restaurant: str
    evenings_closed: int
    first_closed: date | None
    last_closed: date | None
    bookings_written: int
    receipts_written: int
    bookings_before: int
    bookings_after: int
    receipts_before: int
    receipts_after: int

    def text(self) -> str:
        if self.evenings_closed:
            closed = f"{self.evenings_closed} evening(s) closed, {self.first_closed} to {self.last_closed}"
        else:
            closed = "no new evening to close"
        return (
            f"{closed}. Bookings in the table: {self.bookings_before} before, {self.bookings_after} after. "
            f"Receipts: {self.receipts_before} before, {self.receipts_after} after."
        )


# ---- the model of an evening ------------------------------------------------------------------


def _rng(restaurant_id: str, day: date, stream: str) -> random.Random:
    """A random source that depends only on the seed, the restaurant, the day and its purpose."""
    return random.Random(f"{SEED}|{restaurant_id}|{day.isoformat()}|{stream}")


def _around_one(rng: random.Random, spread: float) -> float:
    """A random factor that averages 1."""
    return math.exp(rng.gauss(0.0, spread) - spread * spread / 2)


def _draw(rng: random.Random, table: dict[int, float]) -> int:
    return rng.choices(list(table), weights=list(table.values()))[0]


def weekday_level(weekday: int) -> float:
    """Guests in the book on an ordinary evening of this weekday."""
    return GUESTS_BY_WEEKDAY[weekday] * LEVEL * CALIBRATION


def season_factor(day: date) -> float:
    if day.month == 1:
        if day.day == 1:
            return 1.0   # New Year's Day has its own rule
        return 0.62 if day.day <= 8 else 0.75   # the quiet weeks
    if day.month == 12:
        return 1.10 if day.day <= 23 else 1.0   # December dinners, then the holidays' own rules
    return MONTH_FACTOR[day.month]


def day_level(day: date) -> float:
    """Guests expected in the book that evening in average weather: reservations plus walk-ins."""
    level = weekday_level(day.weekday())
    name = holiday_name(day) or special_name(day)
    if name in DAY_OFF_HOLIDAYS:
        level = max(level, weekday_level(6)) * DAY_OFF_HOLIDAYS[name]
    elif name in OTHER_DAYS:
        level *= OTHER_DAYS[name]
    elif holiday_name(day + timedelta(days=1)) in DAY_OFF_HOLIDAYS and day.weekday() in (0, 1, 2, 3, 6):
        level *= 1.15   # the evening before a day off
    return level * season_factor(day)


def walk_in_weather_factor(weather: dict) -> float:
    """What the day's weather does to walk-ins. Reservations do not depend on the weather."""
    rain, temp, wind = float(weather["rain_mm"]), float(weather["temp_max"]), weather.get("wind_max")
    factor = 1.0
    if rain >= 15:
        factor *= 0.60
    elif rain >= 5:
        factor *= 0.72
    elif rain >= 1:
        factor *= 0.85
    elif temp >= 25:
        factor *= 1.45   # a warm dry evening: the terrace effect
    elif temp >= 20:
        factor *= 1.30
    if temp <= 0:
        factor *= 0.80
    if wind is not None and float(wind) >= 60:
        factor *= 0.85
    return factor


def _arrivals(weekday: int) -> tuple[list[int], list[float]]:
    if weekday in (4, 5):
        return ARRIVALS_WEEKEND
    return ARRIVALS_SUNDAY if weekday == 6 else ARRIVALS_WEEKDAY


def _local(day: date, minutes: int, tz: ZoneInfo) -> datetime:
    """A moment given as a day and minutes after its midnight, local time. 25 * 60 is 01:00 the next day."""
    day, minutes = day + timedelta(days=minutes // 1440), minutes % 1440
    return datetime.combine(day, time(minutes // 60, minutes % 60), tzinfo=tz).astimezone(timezone.utc)


def _party(
    rng: random.Random, restaurant_id: str, day: date, tz: ZoneInfo, kind: str, number: int, size: int, outcome: str | None
) -> Party:
    """One party with everything about it decided now, so it never changes on a later run."""
    weekday = day.weekday()
    slots, weights = _arrivals(weekday)
    visit_minutes = rng.choices(slots, weights=weights)[0]

    if kind == "walk_in":
        created_at = _local(day, visit_minutes, tz)   # entered in the book on arrival
    else:
        lead = rng.choices(range(MAX_LEAD_DAYS + 1), weights=LEAD_WEEKEND if weekday in (4, 5) else LEAD_WEEKDAY)[0]
        if size >= 8:
            lead = min(MAX_LEAD_DAYS, lead + rng.randint(3, 10))   # big groups book earlier
        latest = visit_minutes - 45 if lead == 0 else 22 * 60 + 59
        created_at = _local(day - timedelta(days=lead), rng.randint(8 * 60, latest), tz)

    if outcome is None:
        outcome = "no_show" if kind == "reserved" and rng.random() < NO_SHOW_RATE else "completed"

    table_no = str(rng.randint(1, 58))
    opened_at = _local(day, visit_minutes, tz) + timedelta(minutes=rng.randint(-5, 15))
    stay = min(210, max(55, round(rng.gauss(100 + 6 * (size - 2), 18))))
    change = rng.random()
    guests = size - 1 if change < 0.06 and size > 1 else size + 1 if change > 0.96 else size
    spend = min(85.0, max(22.0, rng.gauss(44.0, 9.0)))
    return Party(
        booking_id=str(uuid.uuid5(NAMESPACE, f"{restaurant_id}|{day.isoformat()}|{kind}|{number}")),
        kind=kind,
        size=size,
        visit_minutes=visit_minutes,
        created_at=created_at,
        table_no=table_no,
        outcome=outcome,
        opened_at=opened_at,
        # Nobody stays more than a quarter of an hour past closing time.
        closed_at=min(opened_at + timedelta(minutes=stay), _local(day, CLOSING_MINUTES[weekday] + 15, tz)),
        guests=guests,
        total=round(guests * spend, 2),
    )


def _fill(rng: random.Random, sizes: dict[int, float], target: float) -> list[int]:
    """Party sizes that add up to about `target` guests."""
    drawn: list[int] = []
    total = 0
    while True:
        size = _draw(rng, sizes)
        if total + size / 2 > target:
            return drawn
        drawn.append(size)
        total += size


def reserved_parties(restaurant: dict, day: date) -> list[Party]:
    """Everyone who reserves for this evening. Depends on the calendar only, never on the weather."""
    restaurant_id, tz = restaurant["id"], ZoneInfo(restaurant["timezone"])
    popularity = _around_one(_rng(restaurant_id, day, "day"), 0.14)
    rng = _rng(restaurant_id, day, "reserved")
    capacity = round(restaurant["seats"] * CAPACITY_TURNS)
    target = min(capacity, day_level(day) * RESERVED_SHARE[day.weekday()] * popularity)

    sizes = _fill(rng, RESERVED_SIZES, target)
    parties = [_party(rng, restaurant_id, day, tz, "reserved", n, size, None) for n, size in enumerate(sizes)]
    # A few bookings that get cancelled. They are extra, so they do not thin out the evening.
    cancelled = sum(rng.random() < CANCELLED_RATE for _ in sizes)
    for n in range(cancelled):
        size = _draw(rng, RESERVED_SIZES)
        parties.append(_party(rng, restaurant_id, day, tz, "reserved", len(sizes) + n, size, "cancelled"))
    return parties


def walk_in_parties(restaurant: dict, day: date, weather: dict, reserved: list[Party]) -> list[Party]:
    """Everyone who walks in. Fewer in the rain, more on a warm dry evening."""
    restaurant_id, tz = restaurant["id"], ZoneInfo(restaurant["timezone"])
    day_rng = _rng(restaurant_id, day, "day")
    popularity = _around_one(day_rng, 0.14)   # the same draw reserved_parties made
    luck = _around_one(day_rng, 0.15)
    target = (
        day_level(day)
        * (1 - RESERVED_SHARE[day.weekday()])
        * math.sqrt(popularity)
        * luck
        * walk_in_weather_factor(weather)
        / WEATHER_NEUTRAL
    )
    capacity = round(restaurant["seats"] * CAPACITY_TURNS)
    seated = sum(party.size for party in reserved if party.outcome == "completed")
    target = min(target, max(0, capacity - seated))   # when it is full, walk-ins are turned away

    rng = _rng(restaurant_id, day, "walk_in")
    sizes = _fill(rng, WALK_IN_SIZES, target)
    return [_party(rng, restaurant_id, day, tz, "walk_in", n, size, "completed") for n, size in enumerate(sizes)]


def _booking_row(restaurant_id: str, day: date, party: Party, status: str) -> dict:
    return {
        "id": party.booking_id,
        "restaurant_id": restaurant_id,
        "visit_date": day.isoformat(),
        "visit_time": f"{party.visit_minutes // 60:02d}:{party.visit_minutes % 60:02d}:00",
        "party_size": party.size,
        "table_no": party.table_no,
        "created_at": party.created_at.isoformat(),
        "status": status,
    }


def _receipt_row(restaurant_id: str, party: Party) -> dict:
    return {
        "id": str(uuid.uuid5(NAMESPACE, f"receipt|{party.booking_id}")),
        "restaurant_id": restaurant_id,
        "opened_at": party.opened_at.isoformat(),
        "closed_at": party.closed_at.isoformat(),
        "table_no": party.table_no,
        "guests": party.guests,
        "total": party.total,
    }


def rows_for_day(restaurant: dict, day: date, *, as_of: datetime, weather: dict | None) -> tuple[list[dict], list[dict]]:
    """The booking and receipt rows for one evening, as the book looks at the moment `as_of`.

    An evening that is over gets its final state: walk-ins, no-shows and receipts. That needs the
    day's measured weather. An evening that is still to come shows only the bookings made so far.
    """
    if not is_open(day):
        return [], []   # closed: nobody books, nobody comes
    restaurant_id = restaurant["id"]
    today = as_of.astimezone(ZoneInfo(restaurant["timezone"])).date()
    reserved = reserved_parties(restaurant, day)

    if day >= today:
        bookings = [
            _booking_row(restaurant_id, day, party, "cancelled" if party.outcome == "cancelled" else "booked")
            for party in reserved
            if party.created_at <= as_of
        ]
        return bookings, []

    if weather is None or weather.get("temp_max") is None or weather.get("rain_mm") is None:
        raise FakeHistoryError(f"no measured weather for {day}, so its walk-ins cannot be worked out")
    parties = reserved + walk_in_parties(restaurant, day, weather, reserved)
    bookings = [_booking_row(restaurant_id, day, party, party.outcome) for party in parties]
    receipts = [_receipt_row(restaurant_id, party) for party in parties if party.outcome == "completed"]
    return bookings, receipts


def generate(
    restaurant: dict, weather_by_day: dict[date, dict], *, first_day: date, as_of: datetime
) -> tuple[list[dict], list[dict]]:
    """All rows from first_day up to 30 days after `as_of`, in memory. Touches no database."""
    today = as_of.astimezone(ZoneInfo(restaurant["timezone"])).date()
    bookings: list[dict] = []
    receipts: list[dict] = []
    day = first_day
    while day <= today + timedelta(days=MAX_LEAD_DAYS):
        day_bookings, day_receipts = rows_for_day(restaurant, day, as_of=as_of, weather=weather_by_day.get(day))
        bookings += day_bookings
        receipts += day_receipts
        day += timedelta(days=1)
    return bookings, receipts


# ---- keeping the database up to date ----------------------------------------------------------


def top_up(db: Database, restaurant: dict, *, as_of: datetime, rebuild: bool = False) -> FeedSummary:
    """Brings the fake book and till in the database up to the moment `as_of`."""
    tz = ZoneInfo(restaurant["timezone"])
    mine = [("restaurant_id", "eq", restaurant["id"])]
    today = as_of.astimezone(tz).date()

    if rebuild:
        db.delete("receipts", mine)
        db.delete("bookings", mine)

    # Evenings that already have receipts are closed for good and are never touched again.
    latest = db.select("receipts", "opened_at", mine, order="opened_at.desc", limit=1)
    closed_through = service_date(parse_moment(latest[0]["opened_at"]), tz) if latest else None

    measured = mine + [("is_forecast", "eq", False)]
    if closed_through is not None:
        measured.append(("date", "gt", closed_through))
    weather_by_day = {
        date.fromisoformat(row["date"]): row
        for row in db.select("daily_weather", "date,temp_max,rain_mm,wind_max", measured, order="date")
    }
    if closed_through is None:
        if not weather_by_day:
            raise FakeHistoryError("there is no measured weather yet; load the weather first")
        first_day = min(weather_by_day)
    else:
        first_day = closed_through + timedelta(days=1)

    bookings, receipts = generate(restaurant, weather_by_day, first_day=first_day, as_of=as_of)

    bookings_before = db.count("bookings", mine)
    receipts_before = db.count("receipts", mine)
    db.upsert("bookings", bookings, on_conflict=["id"])
    db.upsert("receipts", receipts, on_conflict=["id"])
    bookings_after = db.count("bookings", mine)
    receipts_after = db.count("receipts", mine)

    evenings_closed = max(0, (today - first_day).days)
    return FeedSummary(
        restaurant=restaurant["name"],
        evenings_closed=evenings_closed,
        first_closed=first_day if evenings_closed else None,
        last_closed=today - timedelta(days=1) if evenings_closed else None,
        bookings_written=len(bookings),
        receipts_written=len(receipts),
        bookings_before=bookings_before,
        bookings_after=bookings_after,
        receipts_before=receipts_before,
        receipts_after=receipts_after,
    )


def top_up_all(
    db: Database, *, as_of: datetime, rebuild: bool = False, expect_unchanged: bool = False
) -> list[FeedSummary]:
    restaurants = db.select("restaurants", "id,name,timezone,seats", order="name")
    if not restaurants:
        raise FakeHistoryError("there is no restaurant in the database")
    summaries = []
    for restaurant in restaurants:
        summary = top_up(db, restaurant, as_of=as_of, rebuild=rebuild)
        added = (summary.bookings_after - summary.bookings_before) + (summary.receipts_after - summary.receipts_before)
        if expect_unchanged and added:
            raise FakeHistoryError(f"this run added {added} row(s) for {summary.restaurant}; a repeat run must add none")
        summaries.append(summary)
    return summaries


def parse_as_of(text: str | None) -> datetime:
    """The moment to pretend it is. Without one: now."""
    if text is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise FakeHistoryError("--as-of needs a timezone, for example 2026-10-10T03:00:00+02:00")
    return moment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bring the fake bookings and receipts up to date.")
    parser.add_argument("--as-of", help="pretend it is this moment, for example 2026-10-10T03:00:00+02:00")
    parser.add_argument("--expect-unchanged", action="store_true", help="fail if this run adds rows")
    parser.add_argument("--rebuild", action="store_true", help="delete bookings and receipts first (fake data only)")
    args = parser.parse_args(argv)
    title = "Fake bookings, repeat run" if args.expect_unchanged else "Fake bookings"

    try:
        settings = load_settings()
        db = RestDatabase(settings.supabase_url, settings.supabase_secret_key)
        summaries = top_up_all(
            db, as_of=parse_as_of(args.as_of), rebuild=args.rebuild, expect_unchanged=args.expect_unchanged
        )
    except (SettingsError, FakeHistoryError, DatabaseError) as error:
        report.failure(title, str(error))
        return 1

    for summary in summaries:
        report.result(f"{title}: {summary.restaurant}", summary.text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
