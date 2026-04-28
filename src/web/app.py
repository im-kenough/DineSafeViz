"""Flask application for visualizing DineSafe food inspection data.

This module provides a web interface to query and display food safety inspections
from Toronto's DineSafe program, grouped by inspection date with severity-based sorting.
"""
import calendar
import os
from datetime import date, timedelta
from typing import Dict, List, Tuple

import psycopg2
import requests as http_requests
from flask import Flask, render_template, request

app = Flask(__name__)

DATA_START = date(2023, 11, 9)
_QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
SEVERITY_ORDER = {
    "C - Crucial": 0,
    "S - Significant": 1,
    "M - Minor": 2,
    "NA": 3,
    "None": 4
    }


def get_quarter_bounds(year: int, q: int) -> Tuple[date, date]:
    """Get the start and end dates for a given year and quarter.

    The returned dates are clipped to the data availability range (DATA_START to today).

    Args:
        year: The calendar year (e.g., 2023).
        q: The quarter number (1-4, where 1 = Q1 Jan-Mar, 4 = Q4 Oct-Dec).

    Returns:
        A tuple of (start_date, end_date) for the quarter, clipped to valid range.
    """
    month_start, month_end = _QUARTER_MONTHS[q]
    start = date(year, month_start, 1)
    end = date(year, month_end, calendar.monthrange(year, month_end)[1])
    # Clip to available data range: earliest inspection (DATA_START) to today
    return max(start, DATA_START), min(end, date.today())


def get_valid_years() -> List[int]:
    """Get all years from data start to the current year.

    Returns:
        A list of years for which DineSafe data is available.
    """
    return list(range(2023, date.today().year + 1))


def get_valid_quarters(year: int) -> List[int]:
    """Get valid quarters for a given year based on data availability.

    For the current year, only completed quarters are included. Data starts in Q4 2023.
    For other years, all four quarters are valid.

    Args:
        year: The calendar year to query.

    Returns:
        A list of valid quarter numbers (1-4) for the given year.
    """
    today = date.today()
    # Calculate current quarter: month 1-3 = Q1, 4-6 = Q2, 7-9 = Q3, 10-12 = Q4
    current_q = (today.month - 1) // 3 + 1
    if year == 2023:
        # Data starts in Q4 2023, so only Q4 is available
        return [4]
    elif year == today.year:
        # For the current year, include only quarters up to (and including) the current quarter
        return list(range(1, current_q + 1))
    else:
        # For past years, all quarters are available
        return [1, 2, 3, 4]


def parse_year_quarter(args: Dict[str, str]) -> Tuple[int, int]:
    """Parse and validate year and quarter from request arguments.

    Handles invalid or missing values by defaulting to the current year/quarter.
    Invalid values (out of range, non-integer) are silently replaced with defaults.

    Args:
        args: Dictionary of request arguments (typically from Flask request.args).

    Returns:
        A tuple of (year, quarter) with validated values.
    """
    today = date.today()
    current_year = today.year
    valid_years = get_valid_years()

    # Parse and validate year, default to current year
    try:
        year = int(args["year"]) if "year" in args else current_year
    except (ValueError, TypeError):
        year = current_year
    if year not in valid_years:
        year = current_year

    # Parse and validate quarter, default to the latest valid quarter for that year
    valid_qs = get_valid_quarters(year)
    try:
        q = int(args["q"]) if "q" in args else valid_qs[-1]
    except (ValueError, TypeError):
        q = valid_qs[-1]
    if q not in valid_qs:
        q = valid_qs[-1]

    return year, q


def sort_rows(rows: List[Dict]) -> List[Dict]:
    """Sort inspection records by severity level.

    Uses SEVERITY_ORDER to rank inspections from most to least severe.
    Unknown severity values are sorted to the end (order value 5).

    Args:
        rows: List of inspection record dictionaries.

    Returns:
        The same list sorted by severity in ascending order (most severe first).
    """
    return sorted(rows, key=lambda r: SEVERITY_ORDER.get(r.get("severity"), 5))


def build_days(rows: List[Dict], start: date, end: date) -> List[Tuple[date, List[Dict]]]:
    """Group inspections by date and return chronologically (newest first).

    Creates one entry for every date in the range, even if no inspections occurred
    on that date. Inspections on the same date are sorted by severity.

    Args:
        rows: List of inspection record dictionaries with "inspection_date" key.
        start: The earliest date to include.
        end: The latest date to include (search is inclusive).

    Returns:
        A list of (date, inspections) tuples ordered from end to start (newest first).
        Each tuple contains a date and a severity-sorted list of inspections for that date.
    """
    from collections import defaultdict
    # Group all inspections by their inspection date
    by_date = defaultdict(list)
    for row in rows:
        by_date[row["inspection_date"]].append(row)

    # Iterate from end date backwards to start date, creating an entry for each day
    # (even if no inspections occurred that day)
    days = []
    d = end
    while d >= start:
        days.append((d, sort_rows(by_date.get(d, []))))
        d -= timedelta(days=1)
    return days


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "dinesafe"),
    "user": os.environ.get("DB_USER", "dinesafe"),
    "password": os.environ.get("DB_PASSWORD", "dinesafe"),
}


@app.route("/")
def index():
    """Render the main inspection visualization page.

    Fetches inspections for the requested year/quarter, groups them by date,
    and renders the index template with navigation options.

    Query Parameters:
        year (optional): The calendar year to display (defaults to current year).
        q (optional): The quarter to display (defaults to the latest valid quarter).

    Returns:
        Rendered HTML template with inspections grouped by date.
    """
    # Parse and validate year/quarter from request parameters
    year, q = parse_year_quarter(request.args)
    start, end = get_quarter_bounds(year, q)

    # Query database for inspections in the selected quarter
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT inspection_date, severity, action, infraction_details,"
        "       establishment_name, establishment_address, outcome,"
        "       outcome_date, amount_fined"
        " FROM inspections"
        " WHERE inspection_date BETWEEN %s AND %s",
        (start, end),
    )
    # Convert database rows to dictionaries for template rendering
    rows = [
        {
            "inspection_date": r[0],
            "severity": r[1],
            "action": r[2],
            "infraction_details": r[3],
            "establishment_name": r[4],
            "establishment_address": r[5],
            "outcome": r[6],
            "outcome_date": r[7],
            "amount_fined": r[8],
        }
        for r in cur.fetchall()
    ]
    cur.close()
    conn.close()

    # Render template with grouped data and navigation options
    return render_template(
        "index.html",
        days=build_days(rows, start, end),
        selected_year=year,
        selected_q=q,
        valid_years=get_valid_years(),
        valid_quarters=get_valid_quarters(year),
    )


@app.route("/dashboard")
def dashboard():
    """Render the Grafana dashboard iframe page."""
    return render_template("dashboard.html")


GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://grafana:3000")
_grafana_session = http_requests.Session()


@app.route("/grafana/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.route("/grafana/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def grafana_proxy(path):
    """Reverse-proxy requests to the internal Grafana container."""
    url = f"{GRAFANA_URL}/grafana/{path}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    resp = _grafana_session.request(
        method=request.method,
        url=url,
        headers={k: v for k, v in request.headers if k.lower() != "host"},
        data=request.get_data(),
        allow_redirects=False,
    )
    excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
    return resp.content, resp.status_code, headers
