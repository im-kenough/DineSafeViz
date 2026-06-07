import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import get_quarter_bounds, DATA_START


def test_q1_full_quarter():
    start, end = get_quarter_bounds(2024, 1)
    assert start == date(2024, 1, 1)
    assert end == date(2024, 3, 31)


def test_q2_full_quarter():
    start, end = get_quarter_bounds(2024, 2)
    assert start == date(2024, 4, 1)
    assert end == date(2024, 6, 30)


def test_q3_full_quarter():
    start, end = get_quarter_bounds(2024, 3)
    assert start == date(2024, 7, 1)
    assert end == date(2024, 9, 30)


def test_q4_full_quarter():
    start, end = get_quarter_bounds(2024, 4)
    assert start == date(2024, 10, 1)
    assert end == date(2024, 12, 31)


def test_q4_2023_clips_to_data_start():
    # Q4 2023 is Oct 1–Dec 31; DATA_START (2001-01-01) no longer clips
    start, end = get_quarter_bounds(2023, 4)
    assert start == date(2023, 10, 1)
    assert end == date(2023, 12, 31)


def test_end_does_not_exceed_today():
    # Q3 of a future year should clip end to today
    today = date.today()
    start, end = get_quarter_bounds(today.year, (today.month - 1) // 3 + 1)
    assert end <= today


from app import get_valid_years, get_valid_quarters, parse_year_quarter


def test_valid_years_includes_2001_and_current():
    years = get_valid_years()
    assert 2001 in years
    assert date.today().year in years


def test_2023_only_q4():
    assert get_valid_quarters(2023) == [4]


def test_2024_all_four_quarters():
    assert get_valid_quarters(2024) == [1, 2, 3, 4]


def test_parse_valid_params():
    year, q = parse_year_quarter({"year": "2024", "q": "2"})
    assert year == 2024
    assert q == 2


def test_parse_invalid_year_returns_current():
    year, q = parse_year_quarter({"year": "1900", "q": "1"})
    assert year in get_valid_years()


def test_parse_invalid_q_for_2023_returns_4():
    # Only Q4 is valid for 2023; Q1 should fall back to Q4
    year, q = parse_year_quarter({"year": "2023", "q": "1"})
    assert year == 2023
    assert q == 4


def test_parse_non_numeric_params():
    year, q = parse_year_quarter({"year": "abc", "q": "xyz"})
    assert year in get_valid_years()


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


def test_build_days_newest_first():
    rows = [
        {"inspection_date": date(2024, 1, 2), "establishment_status": "Pass"},
        {"inspection_date": date(2024, 1, 1), "establishment_status": "Closed"},
    ]
    start = date(2024, 1, 1)
    end = date(2024, 1, 3)
    days = build_days(rows, start, end)
    assert len(days) == 3
    assert days[0][0] == date(2024, 1, 3)
    assert days[1][0] == date(2024, 1, 2)
    assert days[2][0] == date(2024, 1, 1)


def test_build_days_no_data_day_is_empty_list():
    rows = [{"inspection_date": date(2024, 1, 1), "establishment_status": "Pass"}]
    start = date(2024, 1, 1)
    end = date(2024, 1, 2)
    days = build_days(rows, start, end)
    assert days[0][0] == date(2024, 1, 2)
    assert days[0][1] == []  # Jan 2 has no data


def test_build_days_rows_sorted_within_day():
    rows = [
        {"inspection_date": date(2024, 1, 1), "establishment_status": "Pass"},
        {"inspection_date": date(2024, 1, 1), "establishment_status": "Closed"},
    ]
    start = end = date(2024, 1, 1)
    days = build_days(rows, start, end)
    assert days[0][1][0]["establishment_status"] == "Closed"
    assert days[0][1][1]["establishment_status"] == "Pass"
