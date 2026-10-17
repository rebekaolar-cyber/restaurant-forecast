"""Tests for the two importers: TheFork covers and the manager's roster counts.

Every sample file is made up (see samples/README.md). The database tests run on the throwaway
Postgres as the nightly job's role, so the rights on covers and rosters are tested too.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from forecast import import_covers, import_rosters
from forecast.import_tools import ImportFileError, find_restaurant, read_csv, sql_literal
from forecast.tests.conftest import SAMPLES, SEEDED_RESTAURANT

MONTH = SAMPLES / "thefork_covers_month.csv"
WEEK = SAMPLES / "thefork_covers_week.csv"
DAY = SAMPLES / "thefork_covers_day.csv"
WITH_GUEST_NAME = SAMPLES / "thefork_covers_with_guest_name.csv"
ROSTER = SAMPLES / "roster_counts.csv"
ROSTER_UNKNOWN_ROLE = SAMPLES / "roster_unknown_role.csv"
ROSTER_WITH_NAMES = SAMPLES / "roster_with_names.csv"

COVERS_HEADER = "restaurantName,period,service,channel,offer,covers,bookings,no shows,cancellations,late cancellations"
ONE_ROW = "Restaurant Habibi,2026-10-01,Di-zo,Offline,0,7,3,0,0,0"


def write(tmp_path: Path, name: str, *lines: str) -> Path:
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def covers_rows(owner):
    return owner.execute(
        "select period_start, period_end, service, channel, offer, covers, bookings, no_shows, cancellations, "
        "late_cancellations, source, imported_at from public.covers order by period_start, service, channel, offer"
    ).fetchall()


def roster_rows(owner):
    return owner.execute(
        "select date, shift, role, planned_count, source, imported_at from public.rosters order by date, role"
    ).fetchall()


# ---- the header is the guard ------------------------------------------------------------------


def test_a_file_with_an_extra_column_is_refused_and_the_column_is_named():
    with pytest.raises(ImportFileError, match="refused.*unexpected column\\(s\\): 'guestName'"):
        import_covers.read_file(WITH_GUEST_NAME)


def test_a_file_with_a_different_header_is_refused_with_what_is_missing(tmp_path):
    # TheFork's "combined" export has no service, channel or offer: not this importer's file.
    path = write(tmp_path, "combined.csv", "restaurant,period,covers,bookings,no shows,cancellations,late cancellations",
                 "Restaurant Habibi,2026-10-01,7,3,0,0,0")
    with pytest.raises(ImportFileError) as error:
        import_covers.read_file(path)
    assert "unexpected column(s): 'restaurant'" in str(error.value)
    assert "missing column(s): 'restaurantName', 'service', 'channel', 'offer'" in str(error.value)
    assert "Expected exactly: " + COVERS_HEADER in str(error.value)


def test_the_same_columns_in_another_order_are_refused(tmp_path):
    path = write(tmp_path, "shuffled.csv", "period,restaurantName,service,channel,offer,covers,bookings,no shows,cancellations,late cancellations",
                 "2026-10-01,Restaurant Habibi,Di-zo,Offline,0,7,3,0,0,0")
    with pytest.raises(ImportFileError, match="not in the expected order"):
        import_covers.read_file(path)


def test_a_marker_from_excel_and_windows_line_ends_are_fine(tmp_path):
    path = tmp_path / "excel.csv"
    path.write_bytes(("﻿" + COVERS_HEADER + "\r\n" + ONE_ROW + "\r\n").encode("utf-8"))
    checked = import_covers.read_file(path)
    assert len(checked.rows) == 1 and checked.rows[0]["covers"] == 7


def test_an_empty_file_or_a_header_alone_is_refused(tmp_path):
    with pytest.raises(ImportFileError, match="header is not the one expected"):
        import_covers.read_file(write(tmp_path, "empty.csv", ""))
    with pytest.raises(ImportFileError, match="no rows"):
        import_covers.read_file(write(tmp_path, "header_only.csv", COVERS_HEADER))


def test_a_roster_with_a_name_column_is_refused():
    with pytest.raises(ImportFileError, match="unexpected column\\(s\\): 'name'"):
        import_rosters.read_file(ROSTER_WITH_NAMES)


def test_read_csv_accepts_the_optional_column_only_after_the_required_ones(tmp_path):
    rows = read_csv(write(tmp_path, "ok.csv", "date,role,planned_count,source", "2026-10-09,W,6,rooster"), ("date", "role", "planned_count"), ("source",))
    assert rows == [{"date": "2026-10-09", "role": "W", "planned_count": "6", "source": "rooster"}]
    with pytest.raises(ImportFileError, match="not in the expected order"):
        read_csv(write(tmp_path, "wrong.csv", "date,source,role,planned_count", "2026-10-09,x,W,6"), ("date", "role", "planned_count"), ("source",))


# ---- what a row becomes -----------------------------------------------------------------------


def test_period_is_read_from_the_dates_in_the_file():
    assert import_covers.detect_period([date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]) == "month"
    assert import_covers.detect_period([date(2026, 8, 10), date(2026, 8, 17), date(2026, 8, 31)]) == "week"
    assert import_covers.detect_period([date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5)]) == "day"
    # Mondays, but not whole weeks apart: a daily export that happens to hold Mondays only? No: day.
    assert import_covers.detect_period([date(2026, 8, 10), date(2026, 8, 11)]) == "day"
    # A single Monday the 1st is a month (month is checked first); --period says otherwise if needed.
    assert import_covers.detect_period([date(2026, 6, 1)]) == "month"


def test_month_rows_end_on_the_last_day_of_the_month():
    checked = import_covers.read_file(MONTH)
    assert checked.period == "month" and checked.restaurant == "Restaurant Habibi"
    ends = {row["period_start"]: row["period_end"] for row in checked.rows}
    assert ends == {date(2026, 1, 1): date(2026, 1, 31), date(2026, 2, 1): date(2026, 2, 28), date(2026, 3, 1): date(2026, 3, 31)}
    assert (checked.first_day, checked.last_day) == (date(2026, 1, 1), date(2026, 3, 31))


def test_week_rows_end_on_the_sunday_and_day_rows_on_the_same_day():
    week = import_covers.read_file(WEEK)
    assert week.period == "week"
    assert all(row["period_end"] == row["period_start"] + timedelta(days=6) for row in week.rows)
    day = import_covers.read_file(DAY)
    assert day.period == "day"
    assert all(row["period_end"] == row["period_start"] for row in day.rows)


def test_the_period_can_be_given_and_is_then_checked():
    assert import_covers.read_file(DAY, period="day").period == "day"
    with pytest.raises(ImportFileError, match="line 2: 2026-10-01 is not a Monday, but the period is week"):
        import_covers.read_file(DAY, period="week")
    with pytest.raises(ImportFileError, match="2026-08-10 is not the 1st of a month, but the period is month"):
        import_covers.read_file(WEEK, period="month")
    # A weekly export forced to "day" is allowed: every row then covers its Monday only.
    assert all(row["period_end"] == row["period_start"] for row in import_covers.read_file(WEEK, period="day").rows)


def test_offer_zero_becomes_empty_and_an_empty_service_stays_empty():
    rows = import_covers.read_file(MONTH).rows
    assert {row["offer"] for row in rows} == {"", "Kerstmenu"}
    assert "" in {row["service"] for row in rows}
    assert {row["service"] for row in rows} == {"", "Di-zo", "maandag", "Maandag vanaf 10 augustus"}
    assert all(row["source"] == "thefork" for row in rows)
    jan_offline = next(row for row in rows if row["period_start"] == date(2026, 1, 1) and row["channel"] == "Offline" and row["service"] == "Di-zo")
    assert (jan_offline["covers"], jan_offline["bookings"], jan_offline["no_shows"], jan_offline["cancellations"], jan_offline["late_cancellations"]) == (310, 97, 0, 0, 0)


@pytest.mark.parametrize(
    "row, problem",
    [
        ("Restaurant Habibi,2026-13-01,Di-zo,Offline,0,7,3,0,0,0", "'2026-13-01' is not a date"),
        ("Restaurant Habibi,2026-10-01,Di-zo,Offline,0,-7,3,0,0,0", "covers: '-7' is not a whole number"),
        ("Restaurant Habibi,2026-10-01,Di-zo,Offline,0,7,3.5,0,0,0", "bookings: '3.5' is not a whole number"),
        ("Restaurant Habibi,2026-10-01,Di-zo,,0,7,3,0,0,0", "the channel is empty"),
        ("Restaurant Habibi,2026-10-01,Di-zo,Offline,0,7,3,0,0", "9 values, but the header has 10"),
    ],
)
def test_a_bad_value_names_the_line(tmp_path, row, problem):
    with pytest.raises(ImportFileError, match=f"bad.csv line 2[:,] .*{problem}"):
        import_covers.read_file(write(tmp_path, "bad.csv", COVERS_HEADER, row))


def test_two_restaurant_names_in_one_file_or_a_repeated_key_are_refused(tmp_path):
    with pytest.raises(ImportFileError, match="expected one restaurant name"):
        import_covers.read_file(write(tmp_path, "two.csv", COVERS_HEADER, ONE_ROW, "Other place,2026-10-01,Di-zo,Offline,0,1,1,0,0,0"))
    with pytest.raises(ImportFileError, match="appears more than once"):
        import_covers.read_file(write(tmp_path, "twice.csv", COVERS_HEADER, ONE_ROW, ONE_ROW))


def test_roster_letters_and_words_both_mean_the_same_roles():
    checked = import_rosters.read_file(ROSTER)
    by_day = {}
    for row in checked.rows:
        by_day.setdefault(row["date"], {})[row["role"]] = row["planned_count"]
        assert row["shift"] == "dinner" and row["source"] == "manual"
    assert by_day[date(2026, 10, 9)] == {"servers": 6, "bar_staff": 3, "runners": 2, "food_staff": 3, "cooks": 4}
    assert by_day[date(2026, 10, 10)] == {"servers": 6, "bar_staff": 3, "runners": 3, "food_staff": 4, "cooks": 4}
    assert by_day[date(2026, 10, 11)] == {"servers": 4, "bar_staff": 2, "runners": 2, "food_staff": 3, "cooks": 4}


def test_roster_mistakes_are_refused(tmp_path):
    with pytest.raises(ImportFileError, match="line 3: 'chef' is not a role. Use one of servers, bar_staff"):
        import_rosters.read_file(ROSTER_UNKNOWN_ROLE)
    with pytest.raises(ImportFileError, match="servers on 2026-10-09 appears more than once"):
        import_rosters.read_file(write(tmp_path, "dup.csv", "date,role,planned_count", "2026-10-09,W,6", "2026-10-09,servers,5"))
    with pytest.raises(ImportFileError, match="planned_count: 'six' is not a whole number"):
        import_rosters.read_file(write(tmp_path, "word.csv", "date,role,planned_count", "2026-10-09,W,six"))
    with pytest.raises(ImportFileError, match="'WB' is not a role"):
        import_rosters.read_file(write(tmp_path, "wb.csv", "date,role,planned_count", "2026-10-09,WB,2"))


def test_roster_source_column_is_optional_and_empty_means_manual(tmp_path):
    checked = import_rosters.read_file(write(tmp_path, "src.csv", "date,role,planned_count,source", "2026-10-09,W,6,rooster-app", "2026-10-09,K,4,"))
    assert [row["source"] for row in checked.rows] == ["rooster-app", "manual"]


# ---- which restaurant -------------------------------------------------------------------------


def test_the_restaurant_is_found_by_name_the_way_thefork_writes_it():
    restaurants = [{"id": "a", "name": "Restaurant Habibi"}, {"id": "b", "name": "De Hoek"}]
    assert find_restaurant("Habibi", restaurants)["id"] == "a"        # TheFork drops the word Restaurant
    assert find_restaurant("restaurant habibi", restaurants)["id"] == "a"
    assert find_restaurant("DE HOEK", restaurants)["id"] == "b"
    with pytest.raises(ImportFileError, match="no restaurant called 'Hoek'.*known: 'De Hoek', 'Restaurant Habibi'"):
        find_restaurant("Hoek", restaurants)
    with pytest.raises(ImportFileError, match="more than one restaurant answers to 'Habibi'"):
        find_restaurant("Habibi", restaurants + [{"id": "c", "name": "Habibi"}])


def test_an_unknown_restaurant_stops_the_import_and_nothing_is_written(db, owner, tmp_path):
    other = write(tmp_path, "other.csv", COVERS_HEADER, "Nobody's Place,2026-10-01,Di-zo,Offline,0,7,3,0,0,0")
    with pytest.raises(ImportFileError, match="no restaurant called \"Nobody's Place\""):
        import_covers.import_files(db, [MONTH, other])       # the good file comes first and is still not written
    assert covers_rows(owner) == []


def test_a_roster_needs_no_restaurant_name_while_there_is_only_one(db, owner):
    import_rosters.import_file(db, ROSTER)
    assert len(roster_rows(owner)) == 15
    assert owner.execute("select count(distinct restaurant_id) from public.rosters").fetchone()[0] == 1
    import_rosters.import_file(db, ROSTER, restaurant_name="Habibi")   # naming it is fine too
    with pytest.raises(ImportFileError, match="no restaurant called 'Elsewhere'"):
        import_rosters.import_file(db, ROSTER, restaurant_name="Elsewhere")
    owner.execute("insert into public.restaurants (name, latitude, longitude, timezone, seats) values ('Second place', 0, 0, 'UTC', 10)")
    try:
        with pytest.raises(ImportFileError, match="holds 2 restaurants.*say which with --restaurant"):
            import_rosters.import_file(db, ROSTER)
    finally:
        owner.execute("delete from public.restaurants where name = 'Second place'")


# ---- writing, twice ---------------------------------------------------------------------------


def test_importing_covers_twice_changes_nothing(db, owner):
    first = import_covers.import_files(db, [MONTH, WEEK, DAY])
    assert [(s.rows_read, s.rows_written, s.period) for s in first] == [(16, 16, "month"), (12, 12, "week"), (9, 9, "day")]
    assert [(s.rows_before, s.rows_after) for s in first] == [(0, 16), (16, 28), (28, 37)]
    rows = covers_rows(owner)
    assert len(rows) == 37 and all(row[10] == "thefork" for row in rows)
    assert owner.execute("select count(*) from public.covers where restaurant_id = %s", [SEEDED_RESTAURANT]).fetchone()[0] == 37

    again = import_covers.import_files(db, [MONTH, WEEK, DAY])
    assert [(s.rows_before, s.rows_after) for s in again] == [(37, 37), (37, 37), (37, 37)]
    assert covers_rows(owner) == rows        # the same rows, the same imported_at


def test_a_corrected_export_updates_the_numbers_in_place(db, owner, tmp_path):
    import_covers.import_files(db, [DAY])
    corrected = write(tmp_path, "corrected.csv", COVERS_HEADER, "Restaurant Habibi,2026-10-01,Di-zo,Offline,0,21,6,0,1,0")
    # One row dated the 1st looks like a month to the detector, so the period is said explicitly.
    import_covers.import_files(db, [corrected], period="day")
    rows = covers_rows(owner)
    assert len(rows) == 9
    changed = next(row for row in rows if row[0] == date(2026, 10, 1) and row[3] == "Offline")
    assert changed[5] == 21


def test_importing_a_roster_twice_changes_nothing(db, owner):
    summary = import_rosters.import_file(db, ROSTER)
    assert summary.text() == "15 rows read, 15 rows written (3 evenings, 2026-10-09 to 2026-10-11). Rows in the table: 0 before, 15 after."
    rows = roster_rows(owner)
    assert import_rosters.import_file(db, ROSTER).rows_after == 15
    assert roster_rows(owner) == rows


def test_the_database_refuses_a_role_the_importer_let_through(db):
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation):
        db.upsert("rosters", [{"restaurant_id": SEEDED_RESTAURANT, "date": "2026-10-09", "shift": "dinner", "role": "chef", "planned_count": 1}],
                  on_conflict=["restaurant_id", "date", "shift", "role"])


# ---- printing SQL instead ---------------------------------------------------------------------


def test_sql_mode_prints_statements_without_the_file_name_and_they_work(db, owner, capsys):
    assert import_covers.main([str(MONTH), str(WEEK), "--sql"]) == 0
    out, err = capsys.readouterr()
    for text in (str(MONTH), MONTH.name, str(SAMPLES), "thefork_covers"):
        assert text not in out
    assert out.startswith("begin;\n") and out.endswith("commit;\n")
    assert out.count("insert into public.covers") == 28
    assert "file 1 of 2: 16 rows read, 16 rows written (per month, 2026-01-01 to 2026-03-31)." in out
    assert "file 2 of 2: 12 rows read, 12 rows written (per week, 2026-08-10 to 2026-09-06)." in out
    assert "import stopped: the restaurants table does not hold a restaurant called ''Restaurant Habibi''" in out
    assert f"Covers import: {MONTH.name}: 16 rows read" in err    # the file name goes to the terminal only

    owner.execute(out)
    rows = covers_rows(owner)
    assert len(rows) == 28 and owner.execute("select count(distinct restaurant_id) from public.covers").fetchone()[0] == 1
    owner.execute(out)
    assert covers_rows(owner) == rows


def test_sql_mode_stops_the_whole_script_when_the_restaurant_is_unknown(owner, tmp_path):
    import psycopg

    other = write(tmp_path, "other.csv", COVERS_HEADER, "Nobody's Place,2026-10-01,Di-zo,Offline,0,7,3,0,0,0")
    script, _ = import_covers.sql_for_files([other])
    assert "'nobody''s place'" in script       # the quote is doubled, as SQL wants it
    with pytest.raises(psycopg.errors.RaiseException, match="does not hold a restaurant called \"Nobody's Place\""):
        owner.execute(script)
    owner.execute("rollback")
    assert covers_rows(owner) == []


def test_roster_sql_mode_works_with_and_without_a_restaurant_name(owner, capsys):
    assert import_rosters.main([str(ROSTER), "--sql"]) == 0
    out, err = capsys.readouterr()
    assert ROSTER.name not in out and "15 rows read" in err
    assert out.count("insert into public.rosters") == 15
    assert "does not hold exactly one restaurant" in out
    owner.execute(out)
    assert len(roster_rows(owner)) == 15

    assert import_rosters.main([str(ROSTER), "--sql", "--restaurant", "Habibi"]) == 0
    out, _ = capsys.readouterr()
    assert "lower(r.name) = 'habibi'" in out
    owner.execute(out)
    assert len(roster_rows(owner)) == 15


def test_sql_literal_quotes_text_and_leaves_numbers_and_dates_plain():
    assert sql_literal("Di-zo") == "'Di-zo'"
    assert sql_literal("l'offre") == "'l''offre'"
    assert sql_literal(12) == "12" and sql_literal(date(2026, 1, 1)) == "'2026-01-01'" and sql_literal(None) == "null"
    with pytest.raises(ImportFileError, match="NUL"):
        sql_literal("a\x00b")


# ---- the command ------------------------------------------------------------------------------


def test_the_command_fails_loudly_on_a_bad_file_and_writes_no_sql(capsys):
    assert import_covers.main([str(WITH_GUEST_NAME), "--sql"]) == 1
    out, _ = capsys.readouterr()
    assert out.startswith("FAILED: Covers import: ") and "guestName" in out and "insert into" not in out
    assert import_rosters.main([str(ROSTER_UNKNOWN_ROLE), "--sql"]) == 1
    out, _ = capsys.readouterr()
    assert out.startswith("FAILED: Roster import: ") and "'chef' is not a role" in out


def test_the_command_needs_the_settings_unless_it_prints_sql(monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    assert import_covers.main([str(MONTH)]) == 1
    assert "Missing: SUPABASE_URL and SUPABASE_SECRET_KEY" in capsys.readouterr().out
    assert import_rosters.main([str(ROSTER)]) == 1
    assert "Missing: SUPABASE_URL and SUPABASE_SECRET_KEY" in capsys.readouterr().out
