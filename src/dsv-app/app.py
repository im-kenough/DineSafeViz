"""Flask application for visualizing DineSafe food inspection data.

This module provides a web interface to query and display food safety inspections
from Toronto's DineSafe program, grouped by inspection date with severity-based sorting.
"""
import calendar
import os
import threading
import collections
import itertools
from contextlib import closing
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, abort, render_template, request

app = Flask(__name__)

# Fallback range start, used only when the DB is unreachable or empty
DATA_START = date(2001, 1, 1)
_QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
STATUS_ORDER = {
    "Closed": 0,
    "Conditional Pass": 1,
    "Pass": 2,
}
SEVERITY_ORDER = {
    "C - Crucial": 0,
    "S - Significant": 1,
    "M - Minor": 2,
}
RECENT_YEARS = 4
_stats_cache = {"data": None, "fetched_at": None}
_stats_cache_lock = threading.Lock()
_STATS_TTL = timedelta(days=5)


def get_data_range() -> Tuple[date, date]:
    """Get the first and last inspection dates loaded in the database.

    Uses the cached home stats query. Falls back to DATA_START..today when the
    DB is unreachable (not cached, so the next request retries) or empty.

    Returns:
        A tuple of (first_date, last_date).
    """
    stats = _get_home_stats_or_none()
    if stats is None or stats["min_date"] is None:
        return DATA_START, date.today()
    return stats["min_date"], stats["max_date"]


def get_quarter_bounds(year: int, q: int, first: date) -> Tuple[date, date]:
    """Get the start and end dates for a given year and quarter.

    The returned dates are clipped to the first inspection date and today.

    Args:
        year: The calendar year (e.g., 2023).
        q: The quarter number (1-4, where 1 = Q1 Jan-Mar, 4 = Q4 Oct-Dec).
        first: The first inspection date in the database.

    Returns:
        A tuple of (start_date, end_date) for the quarter, clipped to valid range.
    """
    month_start, month_end = _QUARTER_MONTHS[q]
    start = date(year, month_start, 1)
    end = date(year, month_end, calendar.monthrange(year, month_end)[1])
    return max(start, first), min(end, date.today())


def get_quarter_months(year: int, q: int, first: date) -> List[Tuple[date, date]]:
    """Split a quarter into per-month (start, end) ranges, newest first.

    Each range is clipped to the quarter bounds from get_quarter_bounds.
    """
    start, end = get_quarter_bounds(year, q, first)
    months = []
    for m in range(end.month, start.month - 1, -1):
        month_end = date(year, m, calendar.monthrange(year, m)[1])
        months.append((max(date(year, m, 1), start), min(month_end, end)))
    return months


def get_valid_years(first: date, last: date) -> List[int]:
    """Get all years from the first to the last inspection date.

    Returns:
        A list of years for which DineSafe data is available.
    """
    return list(range(first.year, last.year + 1))


def quarter_of(month: int) -> int:
    """Get the quarter number (1-4) containing a month (1-12)."""
    return (month - 1) // 3 + 1


def get_valid_quarters(year: int, first: date, last: date) -> List[int]:
    """Get valid quarters for a given year based on data availability.

    The first and last years are trimmed to the quarters that contain the
    first and last inspection dates. Other years have all four quarters.

    Args:
        year: The calendar year to query.
        first: The first inspection date in the database.
        last: The last inspection date in the database.

    Returns:
        A list of valid quarter numbers (1-4) for the given year.
    """
    lo = quarter_of(first.month) if year == first.year else 1
    hi = quarter_of(last.month) if year == last.year else 4
    return list(range(lo, hi + 1))


def get_adjacent_quarters(
    year: int, q: int, first: date, last: date
) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """Get the (year, quarter) before and after the given quarter.

    Either side is None when it falls outside the quarters with data.

    Returns:
        A tuple of (previous, next), each a (year, quarter) pair or None.
    """
    prev = (year, q - 1) if q > 1 else (year - 1, 4)
    nxt = (year, q + 1) if q < 4 else (year + 1, 1)
    first_q = (first.year, quarter_of(first.month))
    last_q = (last.year, quarter_of(last.month))
    return (prev if prev >= first_q else None, nxt if nxt <= last_q else None)


def parse_year_quarter(args: Dict[str, str], first: date, last: date) -> Tuple[int, int]:
    """Parse and validate year and quarter from request arguments.

    Handles invalid or missing values by defaulting to the latest year/quarter
    with data. Invalid values (out of range, non-integer) are silently replaced
    with defaults.

    Args:
        args: Dictionary of request arguments (typically from Flask request.args).
        first: The first inspection date in the database.
        last: The last inspection date in the database.

    Returns:
        A tuple of (year, quarter) with validated values.
    """
    valid_years = get_valid_years(first, last)
    latest_year = valid_years[-1]

    # Parse and validate year, default to the latest year with data
    try:
        year = int(args["year"]) if "year" in args else latest_year
    except (ValueError, TypeError):
        year = latest_year
    if year not in valid_years:
        year = latest_year

    # Parse and validate quarter, default to the latest valid quarter for that year
    valid_qs = get_valid_quarters(year, first, last)
    try:
        q = int(args["q"]) if "q" in args else valid_qs[-1]
    except (ValueError, TypeError):
        q = valid_qs[-1]
    if q not in valid_qs:
        q = valid_qs[-1]

    return year, q


def _read_version() -> str:
    try:
        with open(os.path.join(os.path.dirname(__file__), "VERSION.txt"), "r") as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"


_VERSION = _read_version()


@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    first, last = get_data_range()
    years = get_valid_years(first, last)
    year_quarters = [
        (y, get_valid_quarters(y, first, last))
        for y in sorted(years, reverse=True)
    ]
    recent, archive = year_quarters[:RECENT_YEARS], year_quarters[RECENT_YEARS:]
    # Only the inspections page has a selected quarter to highlight in the picker.
    year, q = (
        parse_year_quarter(request.args, first, last)
        if request.endpoint == "index" else (None, None)
    )
    return {
        "current_year": date.today().year,
        "version": _VERSION,
        "recent_year_quarters": recent,
        "archive_year_quarters": archive,
        "archive_open": bool(archive) and year is not None and year <= archive[0][0],
        "selected_year": year,
        "selected_q": q,
    }


def sort_rows(rows: List[Dict]) -> List[Dict]:
    """Sort inspection records by establishment status.

    Uses STATUS_ORDER to rank inspections from most to least severe.
    Unknown status values are sorted to the end (order value 5). Ties are
    broken by name then address so the order is stable across page loads.

    Args:
        rows: List of inspection record dictionaries.

    Returns:
        The same list sorted by status in ascending order (most severe first).
    """
    return sorted(rows, key=lambda r: (
        STATUS_ORDER.get(r.get("establishment_status"), 5),
        r.get("establishment_name") or "",
        r.get("establishment_address") or "",
    ))


def group_establishments(rows: List[Dict]) -> List[Dict]:
    """Group one day's infraction rows into one entry per establishment.

    The dataset has one row per infraction; an establishment's rows on a given
    date form a single inspection with a single status. Rows with no
    infraction details (clean passes) contribute no infractions.

    Args:
        rows: Inspection record dictionaries for a single date.

    Returns:
        A list of establishment dicts in input order. Each has the
        establishment fields plus:

        - "infractions": sorted most severe first, then by category and
          details for a stable order.
        - "severity_counts": a Counter of those infractions by severity.
        - "infraction_groups": those infractions grouped by severity and
          category, in the same order.
    """
    def category_key(r):
        return (
            SEVERITY_ORDER.get(r.get("severity"), 3),
            r.get("severity") or "",
            r.get("infraction_category") or "",
        )

    groups = {}
    for row in rows:
        group = groups.setdefault(row["establishment_id"], {**row, "infractions": []})
        if row.get("infraction_details"):
            group["infractions"].append(row)
    for group in groups.values():
        group["infractions"].sort(key=lambda r: category_key(r) + (r.get("infraction_details") or "",))
        group["severity_counts"] = collections.Counter(r.get("severity") for r in group["infractions"])
        # Sorted by category_key first, so groupby sees each pair contiguously.
        group["infraction_groups"] = [
            {"severity": severity, "category": category, "infractions": list(items)}
            for (_, severity, category), items in itertools.groupby(group["infractions"], key=category_key)
        ]
    return list(groups.values())


def build_days(rows: List[Dict], start: date, end: date) -> List[Tuple[date, List[Dict]]]:
    """Group inspections by date and establishment, newest date first.

    Creates one entry for every date in the range, even if no inspections occurred
    on that date. Establishments on the same date are sorted by status.

    Args:
        rows: List of inspection record dictionaries with "inspection_date" key.
        start: The earliest date to include.
        end: The latest date to include (search is inclusive).

    Returns:
        A list of (date, inspections) tuples ordered from end to start (newest first).
        Each tuple contains a date and a status-sorted list of establishments for that date.
    """
    by_date = collections.defaultdict(list)
    for row in rows:
        by_date[row["inspection_date"]].append(row)

    days = []
    d = end
    while d >= start:
        days.append((d, sort_rows(group_establishments(by_date.get(d, [])))))
        d -= timedelta(days=1)
    return days


DB_CONFIG = {
    "host": os.environ.get("DSV_DB_HOST", "dsv-db"),
    "port": os.environ.get("DSV_DB_PORT", "5432"),
    "dbname": os.environ.get("DSV_DB_NAME", "dinesafe"),
    "user": os.environ.get("DSV_DB_USER", "dinesafe"),
    "password": os.environ.get("DSV_DB_PASSWORD", "dinesafe"),
}


def _cached_stats(now: datetime):
    """Return cached stats if still fresh, else None."""
    fetched_at = _stats_cache["fetched_at"]
    if fetched_at is not None and now - fetched_at <= _STATS_TTL:
        return _stats_cache["data"]
    return None


def _get_home_stats() -> Dict:
    now = datetime.now()
    cached = _cached_stats(now)
    if cached is not None:
        return cached

    # Serialize cache fills so concurrent gthread workers don't stampede the DB.
    with _stats_cache_lock:
        cached = _cached_stats(now)
        if cached is not None:
            return cached

        with closing(psycopg2.connect(**DB_CONFIG, connect_timeout=5)) as conn, \
                closing(conn.cursor()) as cur:
            # One row per infraction, so count distinct inspections, not rows.
            # An inspection is an (establishment, date) pair: recent rows have
            # no inspection_id. The Grafana dashboard counts the same way.
            cur.execute(
                "SELECT COUNT(*), MIN(inspection_date), MAX(inspection_date)"
                " FROM (SELECT DISTINCT establishment_id, inspection_date FROM inspections) v"
            )
            total, min_date, max_date = cur.fetchone()

        years_of_data = 0
        if min_date is not None and max_date is not None:
            years_of_data = max_date.year - min_date.year + 1

        stats = {
            "total_inspections": total, "years_of_data": years_of_data,
            "min_date": min_date, "max_date": max_date,
        }
        # Empty table means the first seed hasn't committed yet; don't cache it.
        if total:
            _stats_cache["data"] = stats
            _stats_cache["fetched_at"] = now
        return stats


def _get_home_stats_or_none() -> Optional[Dict]:
    """Return the home stats, or None when the DB is unreachable."""
    try:
        return _get_home_stats()
    except psycopg2.Error:
        return None


@app.route("/")
def home():
    return render_template("home.html", stats=_get_home_stats())


def _fetch_inspections(start: date, end: date) -> List[Dict]:
    """Fetch inspection rows between start and end (inclusive)."""
    with closing(psycopg2.connect(**DB_CONFIG, connect_timeout=5)) as conn, \
            closing(conn.cursor(cursor_factory=RealDictCursor)) as cur:
        cur.execute(
            "SELECT inspection_date, establishment_status, action, infraction_details,"
            "       establishment_name, establishment_address, establishment_type,"
            "       street, unit, postal_code,"
            "       outcome, outcome_date, amount_fined,"
            "       establishment_id, severity,"
            "       infraction_category"
            " FROM inspections"
            " WHERE inspection_date BETWEEN %s AND %s",
            (start, end),
        )
        return cur.fetchall()


@app.route("/inspections")
def index():
    """Render the main inspection visualization page.

    Renders one collapsible section per month of the requested year/quarter.
    Only the latest month's inspections are queried and rendered; older
    months are fetched from inspections_month when first expanded.

    Query Parameters:
        year (optional): The calendar year to display (defaults to current year).
        q (optional): The quarter to display (defaults to the latest valid quarter).

    Returns:
        Rendered HTML template with the latest month's inspections grouped by date.
    """
    first, last = get_data_range()
    year, q = parse_year_quarter(request.args, first, last)
    months = get_quarter_months(year, q, first)
    start, end = months[-1][0], months[0][1]
    latest_start, latest_end = months[0]
    rows = _fetch_inspections(latest_start, latest_end)
    prev_q, next_q = get_adjacent_quarters(year, q, first, last)

    return render_template(
        "index.html",
        days=build_days(rows, latest_start, latest_end),
        months=months,
        start=start,
        end=end,
        prev_q=prev_q,
        next_q=next_q,
    )


@app.route("/inspections/month")
def inspections_month():
    """Render one month's day boxes as an HTML fragment.

    Query Parameters:
        year: The calendar year.
        m: The month number (1-12).

    Returns:
        The day boxes for that month, or 404 if the month is malformed or
        outside the data range.
    """
    try:
        year, m = int(request.args["year"]), int(request.args["m"])
    except (KeyError, ValueError):
        abort(404)
    first, last = get_data_range()
    q = quarter_of(m)
    if year not in get_valid_years(first, last) or q not in get_valid_quarters(year, first, last):
        abort(404)
    months = {s.month: (s, e) for s, e in get_quarter_months(year, q, first)}
    if m not in months:
        abort(404)
    start, end = months[m]
    rows = _fetch_inspections(start, end)
    return render_template("_days.html", days=build_days(rows, start, end))


@app.route("/dashboard")
def dashboard():
    """Render the Grafana dashboard iframe page."""
    return render_template("dashboard.html")


@app.route("/info")
def info():
    """Render the information page about DineSafe and the dataset."""
    return render_template("info.html", stats=_get_home_stats_or_none())


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/readyz")
def readyz():
    try:
        with closing(psycopg2.connect(**DB_CONFIG, connect_timeout=1)) as conn, \
                closing(conn.cursor()) as cur:
            cur.execute("SELECT 1")
        return "ok", 200
    except Exception:
        return "db unreachable", 503

