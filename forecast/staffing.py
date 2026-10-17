"""Turns a guest number into staff per role, using the manager's own table.

The model only predicts guests. Staff numbers always come from this rule, never from the model.

The table (staffing_rules) has one row per guest level. A row applies from its guest number up
to the next row. With fewer guests than the first row, the first row applies: it is the smallest
roster the manager ever plans.
"""

from __future__ import annotations

from collections.abc import Sequence

from forecast.db import Database

# Database column -> what it is on the manager's roster.
ROLES = {
    "servers": "floor (W)",
    "bar_staff": "bar (B)",
    "runners": "runner (R)",
    "food_staff": "food (F)",
    "cooks": "kitchen (fixed crew, not on the roster)",
}


class StaffingError(RuntimeError):
    """The staffing table is missing or makes no sense."""


def load_bands(db: Database, restaurant_id: str) -> list[dict]:
    bands = db.select(
        "staffing_rules",
        "guests_from," + ",".join(ROLES),
        [("restaurant_id", "eq", restaurant_id)],
        order="guests_from",
    )
    if not bands:
        raise StaffingError("the staffing table is empty, so guests cannot be turned into staff")
    return bands


def staff_for(guests: int, bands: Sequence[dict]) -> dict[str, int]:
    """Staff per role for this many guests: {"servers": 4, "bar_staff": 2, ...}."""
    if not bands:
        raise StaffingError("the staffing table is empty, so guests cannot be turned into staff")
    if guests < 0:
        raise StaffingError(f"a guest number cannot be negative ({guests})")
    ordered = sorted(bands, key=lambda band: band["guests_from"])
    chosen = ordered[0]
    for band in ordered:
        if band["guests_from"] <= guests:
            chosen = band
    return {role: int(chosen[role]) for role in ROLES}


def roster_text(staff: dict[str, int]) -> str:
    """The manager's shorthand, for logs: '4W 2B 2R 3F + 4 kitchen'."""
    return (
        f"{staff['servers']}W {staff['bar_staff']}B {staff['runners']}R {staff['food_staff']}F "
        f"+ {staff['cooks']} kitchen"
    )
