import calendar
import os
from datetime import date, timedelta

import psycopg2
from flask import Flask, render_template, request

app = Flask(__name__)

DATA_START = date(2023, 11, 9)
_QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
SEVERITY_ORDER = {"C - Crucial": 0, "S - Significant": 1, "M - Minor": 2}


def get_quarter_bounds(year, q):
    """Return (start, end) dates for year/quarter, clipped to DATA_START and today."""
    month_start, month_end = _QUARTER_MONTHS[q]
    start = date(year, month_start, 1)
    end = date(year, month_end, calendar.monthrange(year, month_end)[1])
    return max(start, DATA_START), min(end, date.today())


def get_valid_years():
    return list(range(2023, date.today().year + 1))


def get_valid_quarters(year):
    today = date.today()
    current_q = (today.month - 1) // 3 + 1
    if year == 2023:
        return [4]
    elif year == today.year:
        return list(range(1, current_q + 1))
    else:
        return [1, 2, 3, 4]


def parse_year_quarter(args):
    today = date.today()
    current_year = today.year
    valid_years = get_valid_years()

    try:
        year = int(args["year"]) if "year" in args else current_year
    except (ValueError, TypeError):
        year = current_year
    if year not in valid_years:
        year = current_year

    valid_qs = get_valid_quarters(year)
    try:
        q = int(args["q"]) if "q" in args else valid_qs[-1]
    except (ValueError, TypeError):
        q = valid_qs[-1]
    if q not in valid_qs:
        q = valid_qs[-1]

    return year, q


DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "dinesafe"),
    "user": os.environ.get("DB_USER", "dinesafe"),
    "password": os.environ.get("DB_PASSWORD", "dinesafe"),
}


@app.route("/")
def index():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT inspection_date, establishment_name, severity "
        "FROM inspections ORDER BY inspection_date DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    inspections = []
    for date, name, severity in rows:
        if severity:
            violation = f"Yes — {severity}"
        else:
            violation = "No"
        inspections.append({"date": date, "name": name, "violation": violation})

    return render_template("index.html", inspections=inspections)
