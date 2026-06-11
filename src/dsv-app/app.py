"""Flask application for visualizing DineSafe food inspection data.

This module provides a web interface to query and display food safety inspections
from Toronto's DineSafe program, grouped by inspection date with severity-based sorting.
"""
import calendar
import logging
import os
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import psycopg2
from flask import Flask, g, render_template, request
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

app = Flask(__name__)

_logger = logging.getLogger("dsv-app")
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(
    jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
)
_logger.addHandler(_log_handler)
_logger.setLevel(logging.INFO)

metrics = PrometheusMetrics(app)
_db_query_duration = Histogram(
    "dsv_db_query_duration_seconds", "DB query latency", ["route"]
)
_stats_cache_hits = Counter("dsv_stats_cache_hits_total", "Stats cache hits")
_stats_cache_misses = Counter("dsv_stats_cache_misses_total", "Stats cache misses")
_inspection_rows_returned = Histogram(
    "dsv_inspection_query_rows", "Inspection rows per /inspections request"
)

_otel_provider = TracerProvider()
_otel_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(_otel_provider)
FlaskInstrumentor().instrument_app(app)
Psycopg2Instrumentor().instrument()

DATA_START = date(2001, 1, 1)
_QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
STATUS_ORDER = {
    "Closed": 0,
    "Conditional Pass": 1,
    "Pass": 2,
}
RECENT_YEARS = 4
# The recent CSV only covers from Q4 2023 onward; historical data ends 2022.
RECENT_DATA_START_YEAR = 2023
_stats_cache = {"data": None, "fetched_at": None}
_STATS_TTL = timedelta(days=5)


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
    return list(range(2001, date.today().year + 1))


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
    if year == RECENT_DATA_START_YEAR:
        # Historical data ends 2022; recent CSV only goes back to Q4 2023
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


def _read_version() -> str:
    try:
        with open(os.path.join(os.path.dirname(__file__), "VERSION.txt"), "r") as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"


_VERSION = _read_version()


@app.before_request
def _before_request():
    g.request_id = str(uuid.uuid4())
    g.start_time = time.monotonic()


@app.after_request
def _after_request(response):
    start = getattr(g, "start_time", None)
    duration_ms = round((time.monotonic() - start) * 1000, 2) if start is not None else None
    _logger.info(
        "request",
        extra={
            "request_id": getattr(g, "request_id", None),
            "route": request.endpoint,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "remote_addr": request.remote_addr,
            "user_agent": request.user_agent.string,
        },
    )
    request_id = getattr(g, "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    year, q = parse_year_quarter(request.args)
    years = get_valid_years()
    year_quarters = [
        (y, get_valid_quarters(y))
        for y in sorted(years, reverse=True)
    ]
    return {
        "current_year": date.today().year,
        "version": _VERSION,
        "recent_year_quarters": year_quarters[:RECENT_YEARS],
        "archive_year_quarters": year_quarters[RECENT_YEARS:],
        "selected_year": year,
        "selected_q": q,
    }


def sort_rows(rows: List[Dict]) -> List[Dict]:
    """Sort inspection records by establishment status.

    Uses STATUS_ORDER to rank inspections from most to least severe.
    Unknown status values are sorted to the end (order value 5).

    Args:
        rows: List of inspection record dictionaries.

    Returns:
        The same list sorted by status in ascending order (most severe first).
    """
    return sorted(rows, key=lambda r: STATUS_ORDER.get(r.get("establishment_status"), 5))


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
    by_date = defaultdict(list)
    for row in rows:
        by_date[row["inspection_date"]].append(row)

    days = []
    d = end
    while d >= start:
        days.append((d, sort_rows(by_date.get(d, []))))
        d -= timedelta(days=1)
    return days


DB_CONFIG = {
    "host": os.environ.get("DSV_DB_HOST", "dsv-db"),
    "port": os.environ.get("DSV_DB_PORT", "5432"),
    "dbname": os.environ.get("DSV_DB_NAME", "dinesafe"),
    "user": os.environ.get("DSV_DB_USER", "dinesafe"),
    "password": os.environ.get("DSV_DB_PASSWORD", "dinesafe"),
}


def _get_home_stats() -> Dict[str, int]:
    now = datetime.now()
    if (
        _stats_cache["fetched_at"] is not None
        and now - _stats_cache["fetched_at"] <= _STATS_TTL
    ):
        _stats_cache_hits.inc()
        return _stats_cache["data"]

    _stats_cache_misses.inc()
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        with _db_query_duration.labels(route="home").time():
            cur.execute(
                "SELECT COUNT(*), MIN(inspection_date), MAX(inspection_date) FROM inspections"
            )
            total, min_date, max_date = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    years_of_data = 0
    if min_date is not None and max_date is not None:
        years_of_data = max_date.year - min_date.year + 1

    stats = {"total_inspections": total, "years_of_data": years_of_data}
    _stats_cache["data"] = stats
    _stats_cache["fetched_at"] = now
    return stats


@app.route("/")
def home():
    return render_template("home.html", stats=_get_home_stats())


@app.route("/inspections")
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
    year, q = parse_year_quarter(request.args)
    start, end = get_quarter_bounds(year, q)

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        with _db_query_duration.labels(route="inspections").time():
            cur.execute(
                "SELECT inspection_date, establishment_status, action, infraction_details,"
                "       establishment_name, establishment_address, establishment_type,"
                "       outcome, outcome_date, amount_fined"
                " FROM inspections"
                " WHERE inspection_date BETWEEN %s AND %s",
                (start, end),
            )
            raw_rows = cur.fetchall()
        _inspection_rows_returned.observe(len(raw_rows))
        cur.close()
    finally:
        conn.close()

    rows = [
        {
            "inspection_date": r[0],
            "establishment_status": r[1],
            "action": r[2],
            "infraction_details": r[3],
            "establishment_name": r[4],
            "establishment_address": r[5],
            "establishment_type": r[6],
            "outcome": r[7],
            "outcome_date": r[8],
            "amount_fined": r[9],
        }
        for r in raw_rows
    ]

    return render_template(
        "index.html",
        days=build_days(rows, start, end),
    )


@app.route("/dashboard")
def dashboard():
    """Render the Grafana dashboard iframe page."""
    return render_template("dashboard.html")


@app.route("/info")
def info():
    """Render the information page about DineSafe and the dataset."""
    return render_template("info.html")


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/readyz")
def readyz():
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=1)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        finally:
            conn.close()
        return "ok", 200
    except Exception:
        return "db unreachable", 503

