"""What the forecast is allowed to look at: guests per past evening, and the reservation book.

Guests per evening come from receipts (what really happened). The reservation book comes from
bookings, and can be asked "how many guests were already booked for this evening at that moment?".
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from forecast.db import Database

# Friday and Saturday run past midnight. Anything before 06:00 belongs to the evening before.
SERVICE_DAY_STARTS_AT_HOUR = 6


def parse_moment(text: str) -> datetime:
    """Reads a timestamp as the database sends it. Always returns a time with a timezone."""
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError(f"timestamp without a timezone: {text}")
    return moment


def service_date(moment: datetime, tz: ZoneInfo) -> date:
    """The evening a moment belongs to: 00:30 on Sunday morning is still Saturday's shift."""
    return (moment.astimezone(tz) - timedelta(hours=SERVICE_DAY_STARTS_AT_HOUR)).date()


def local_moment(day: date, at: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, at, tzinfo=tz)


class History:
    """Guests per evening and the reservation book, held in memory."""

    def __init__(self, tz: ZoneInfo, guests_by_day: dict[date, int], bookings: Iterable[tuple[date, datetime, int]]):
        """`bookings` are (visit day, moment the booking was made, party size); cancelled ones left out."""
        self.tz = tz
        self._guests = dict(guests_by_day)
        made: dict[date, list[tuple[datetime, int]]] = defaultdict(list)
        for visit_day, created_at, party_size in bookings:
            made[visit_day].append((created_at.astimezone(timezone.utc), party_size))
        self._made_at: dict[date, list[datetime]] = {}
        self._running_total: dict[date, list[int]] = {}
        for visit_day, entries in made.items():
            entries.sort()
            total, totals = 0, []
            for _, party_size in entries:
                total += party_size
                totals.append(total)
            self._made_at[visit_day] = [created_at for created_at, _ in entries]
            self._running_total[visit_day] = totals

    @classmethod
    def from_rows(cls, tz: ZoneInfo, booking_rows: Iterable[dict], receipt_rows: Iterable[dict]) -> "History":
        """Builds the history from rows shaped like the bookings and receipts tables."""
        guests: dict[date, int] = defaultdict(int)
        for row in receipt_rows:
            guests[service_date(parse_moment(row["opened_at"]), tz)] += int(row["guests"])
        bookings = (
            (date.fromisoformat(row["visit_date"]), parse_moment(row["created_at"]), int(row["party_size"]))
            for row in booking_rows
            if row["status"] != "cancelled"
        )
        return cls(tz, guests, bookings)

    def guests(self, day: date) -> int | None:
        """Guests served that evening, or None if there are no receipts for it."""
        return self._guests.get(day)

    def days_with_guests(self) -> list[date]:
        return sorted(self._guests)

    def booked(self, day: date, as_of: datetime) -> int:
        """Guests in the reservation book for that evening, counting only bookings made by `as_of`."""
        made_at = self._made_at.get(day)
        if not made_at:
            return 0
        position = bisect_right(made_at, as_of.astimezone(timezone.utc))
        return self._running_total[day][position - 1] if position else 0


def load_history(db: Database, restaurant: dict, *, first_day: date, last_day: date) -> History:
    """Reads receipts and bookings for the evenings from first_day to last_day (both included)."""
    tz = ZoneInfo(restaurant["timezone"])
    mine = [("restaurant_id", "eq", restaurant["id"])]
    day_start = time(SERVICE_DAY_STARTS_AT_HOUR)
    receipts = db.select(
        "receipts",
        "opened_at,guests",
        mine
        + [
            ("opened_at", "gte", local_moment(first_day, day_start, tz)),
            ("opened_at", "lt", local_moment(last_day + timedelta(days=1), day_start, tz)),
        ],
        order="opened_at,id",
    )
    bookings = db.select(
        "bookings",
        "visit_date,created_at,party_size,status",
        mine + [("visit_date", "gte", first_day), ("visit_date", "lte", last_day)],
        order="visit_date,id",
    )
    return History.from_rows(tz, bookings, receipts)
