from datetime import date
from unittest.mock import MagicMock, patch

import psycopg2

import app as app_module
from app import (
    DATA_START, get_data_range, get_quarter_bounds, get_quarter_months, get_valid_quarters,
    get_valid_years, parse_year_quarter,
)

# A DB range narrower than 2001..today: starts mid-Q2 2010, ends in Q1 2025.
FIRST = date(2010, 6, 1)
LAST = date(2025, 2, 1)


def test_q1_full_quarter():
    start, end = get_quarter_bounds(2024, 1, FIRST)
    assert start == date(2024, 1, 1)
    assert end == date(2024, 3, 31)


def test_q2_full_quarter():
    start, end = get_quarter_bounds(2024, 2, FIRST)
    assert start == date(2024, 4, 1)
    assert end == date(2024, 6, 30)


def test_q3_full_quarter():
    start, end = get_quarter_bounds(2024, 3, FIRST)
    assert start == date(2024, 7, 1)
    assert end == date(2024, 9, 30)


def test_q4_full_quarter():
    start, end = get_quarter_bounds(2024, 4, FIRST)
    assert start == date(2024, 10, 1)
    assert end == date(2024, 12, 31)


def test_first_quarter_start_clips_to_first_inspection():
    start, end = get_quarter_bounds(2010, 2, FIRST)
    assert start == FIRST
    assert end == date(2010, 6, 30)


def test_end_does_not_exceed_today():
    today = date.today()
    start, end = get_quarter_bounds(today.year, (today.month - 1) // 3 + 1, FIRST)
    assert end <= today


def test_quarter_months_newest_first():
    assert get_quarter_months(2024, 1, FIRST) == [
        (date(2024, 3, 1), date(2024, 3, 31)),
        (date(2024, 2, 1), date(2024, 2, 29)),
        (date(2024, 1, 1), date(2024, 1, 31)),
    ]


def test_quarter_months_clipped_to_first_inspection():
    # FIRST is 2010-06-01, so Q2 2010 only has June.
    assert get_quarter_months(2010, 2, FIRST) == [(FIRST, date(2010, 6, 30))]


def test_quarter_months_stop_at_today():
    today = date.today()
    months = get_quarter_months(today.year, (today.month - 1) // 3 + 1, FIRST)
    assert months[0] == (today.replace(day=1), today)


def test_valid_years_match_db_range():
    assert get_valid_years(FIRST, LAST) == list(range(2010, 2026))


def test_valid_quarters_first_year_starts_at_first_quarter_with_data():
    assert get_valid_quarters(2010, FIRST, LAST) == [2, 3, 4]


def test_valid_quarters_last_year_ends_at_last_quarter_with_data():
    assert get_valid_quarters(2025, FIRST, LAST) == [1]


def test_valid_quarters_middle_year_all_four():
    assert get_valid_quarters(2023, FIRST, LAST) == [1, 2, 3, 4]


def test_valid_quarters_single_year_range():
    assert get_valid_quarters(2024, date(2024, 4, 5), date(2024, 8, 1)) == [2, 3]


def test_parse_valid_params():
    assert parse_year_quarter({"year": "2024", "q": "2"}, FIRST, LAST) == (2024, 2)


def test_parse_missing_params_defaults_to_latest_quarter_with_data():
    assert parse_year_quarter({}, FIRST, LAST) == (2025, 1)


def test_parse_year_outside_db_range_defaults_to_latest():
    assert parse_year_quarter({"year": "2005", "q": "1"}, FIRST, LAST) == (2025, 1)


def test_parse_quarter_before_first_inspection_falls_back():
    assert parse_year_quarter({"year": "2010", "q": "1"}, FIRST, LAST) == (2010, 4)


def test_parse_non_numeric_params():
    assert parse_year_quarter({"year": "abc", "q": "xyz"}, FIRST, LAST) == (2025, 1)


def _stats_db(total, min_date, max_date):
    conn = MagicMock()
    conn.cursor.return_value.fetchone.return_value = (total, min_date, max_date)
    return conn


def _clear_cache():
    app_module._stats_cache["data"] = None
    app_module._stats_cache["fetched_at"] = None


def test_data_range_comes_from_db():
    _clear_cache()
    with patch("app.psycopg2.connect", return_value=_stats_db(10, FIRST, LAST)):
        assert get_data_range() == (FIRST, LAST)


def test_data_range_falls_back_when_db_empty():
    _clear_cache()
    with patch("app.psycopg2.connect", return_value=_stats_db(0, None, None)):
        assert get_data_range() == (DATA_START, date.today())


def test_data_range_falls_back_when_db_unreachable_and_does_not_cache():
    _clear_cache()
    with patch("app.psycopg2.connect", side_effect=psycopg2.OperationalError("down")):
        assert get_data_range() == (DATA_START, date.today())
    assert app_module._stats_cache["fetched_at"] is None


from app import sort_rows, build_days


def test_sort_rows_closed_first():
    rows = [
        {"establishment_status": "Pass", "action": "a"},
        {"establishment_status": "Closed", "action": "b"},
        {"establishment_status": "Conditional Pass", "action": "c"},
        {"establishment_status": None, "action": "d"},
    ]
    result = sort_rows(rows)
    assert [r["establishment_status"] for r in result] == [
        "Closed", "Conditional Pass", "Pass", None
    ]


def test_sort_rows_pass_last():
    rows = [
        {"establishment_status": "Pass", "action": "a"},
        {"establishment_status": "Conditional Pass", "action": "b"},
    ]
    result = sort_rows(rows)
    assert result[0]["establishment_status"] == "Conditional Pass"
    assert result[1]["establishment_status"] == "Pass"


def _row(d, est_id, status, **extra):
    row = {
        "inspection_date": d,
        "establishment_id": est_id,
        "establishment_status": status,
        "establishment_name": f"Est {est_id}",
        "establishment_address": "1 Main St",
        "establishment_type": "Restaurant",
        "infraction_details": None,
        "severity": None,
    }
    row.update(extra)
    return row


def test_build_days_newest_first():
    rows = [
        _row(date(2024, 1, 2), "1", "Pass"),
        _row(date(2024, 1, 1), "2", "Closed"),
    ]
    start = date(2024, 1, 1)
    end = date(2024, 1, 3)
    days = build_days(rows, start, end)
    assert len(days) == 3
    assert days[0][0] == date(2024, 1, 3)
    assert days[1][0] == date(2024, 1, 2)
    assert days[2][0] == date(2024, 1, 1)


def test_build_days_no_data_day_is_empty_list():
    rows = [_row(date(2024, 1, 1), "1", "Pass")]
    start = date(2024, 1, 1)
    end = date(2024, 1, 2)
    days = build_days(rows, start, end)
    assert days[0][0] == date(2024, 1, 2)
    assert days[0][1] == []  # Jan 2 has no data


def test_build_days_establishments_sorted_within_day():
    rows = [
        _row(date(2024, 1, 1), "1", "Pass"),
        _row(date(2024, 1, 1), "2", "Closed"),
    ]
    start = end = date(2024, 1, 1)
    days = build_days(rows, start, end)
    assert days[0][1][0]["establishment_status"] == "Closed"
    assert days[0][1][1]["establishment_status"] == "Pass"


def test_build_days_groups_infractions_by_establishment():
    d = date(2024, 1, 1)
    rows = [
        _row(d, "1", "Conditional Pass", infraction_details="Minor thing", severity="M - Minor"),
        _row(d, "1", "Conditional Pass", infraction_details="Crucial thing", severity="C - Crucial"),
        _row(d, "2", "Pass"),
    ]
    days = build_days(rows, d, d)
    groups = days[0][1]
    assert len(groups) == 2
    first = groups[0]
    assert first["establishment_name"] == "Est 1"
    # infractions sorted most severe first
    assert [i["infraction_details"] for i in first["infractions"]] == [
        "Crucial thing", "Minor thing"
    ]


def test_build_days_clean_pass_has_no_infractions():
    d = date(2024, 1, 1)
    days = build_days([_row(d, "1", "Pass")], d, d)
    assert days[0][1][0]["infractions"] == []


def test_sort_rows_ties_broken_by_name():
    rows = [
        {"establishment_status": "Pass", "establishment_name": "Zed Cafe"},
        {"establishment_status": "Pass", "establishment_name": None},
        {"establishment_status": "Pass", "establishment_name": "Able Diner"},
    ]
    assert [r["establishment_name"] for r in sort_rows(rows)] == [None, "Able Diner", "Zed Cafe"]


def test_build_days_infraction_ties_broken_by_category_then_details():
    d = date(2024, 1, 1)
    rows = [
        _row(d, "1", "Pass", infraction_details="b", infraction_category="05", severity="M - Minor"),
        _row(d, "1", "Pass", infraction_details="z", infraction_category="02", severity="M - Minor"),
        _row(d, "1", "Pass", infraction_details="a", infraction_category="05", severity="M - Minor"),
    ]
    infractions = build_days(rows, d, d)[0][1][0]["infractions"]
    assert [i["infraction_details"] for i in infractions] == ["z", "a", "b"]
