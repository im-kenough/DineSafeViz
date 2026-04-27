# Day-Grouped Inspection Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat inspection table with a day-grouped layout: year/quarter tabs, one rounded box per calendar day, and a severity-sorted mini-table per day.

**Architecture:** Pure server-side Flask. URL params `?year=&q=` drive a DB query scoped to the selected quarter; Python helper functions (no DB dependency) handle date math, severity sorting, and day-map construction. The template loops over a pre-built list of `(date, rows)` pairs.

**Tech Stack:** Python 3.12, Flask 3.1.1, psycopg2-binary 2.9.10, pytest, Jinja2 (bundled with Flask)

---

## File Map

| File | Change |
|---|---|
| `src/web/requirements-dev.txt` | **Create** — pytest dev dependency (kept out of Dockerfile) |
| `src/web/tests/__init__.py` | **Create** — empty, marks directory as package |
| `src/web/tests/test_helpers.py` | **Create** — tests for all pure helper functions |
| `src/web/tests/test_routes.py` | **Create** — Flask test-client tests for the route |
| `src/web/app.py` | **Modify** — add helpers, update route query and response |
| `src/web/templates/index.html` | **Modify** — full replacement with day-box layout |

---

## Task 1: Set up pytest and test skeleton

**Files:**
- Create: `src/web/requirements-dev.txt`
- Create: `src/web/tests/__init__.py`
- Create: `src/web/tests/test_helpers.py`

- [ ] **Step 1: Create dev requirements file**

```
# src/web/requirements-dev.txt
pytest==8.3.5
```

- [ ] **Step 2: Install pytest**

Run from `src/web/`:
```bash
pip install -r requirements-dev.txt
```
Expected: `Successfully installed pytest-8.3.5` (or similar)

- [ ] **Step 3: Create test package marker**

```python
# src/web/tests/__init__.py
```
(empty file)

- [ ] **Step 4: Create test_helpers.py skeleton**

```python
# src/web/tests/test_helpers.py
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
```

- [ ] **Step 5: Verify pytest discovers the test file**

Run from `src/web/`:
```bash
pytest tests/ -v
```
Expected output: `no tests ran` (0 collected, 0 errors — just confirming discovery works)

- [ ] **Step 6: Commit**

```bash
git add src/web/requirements-dev.txt src/web/tests/__init__.py src/web/tests/test_helpers.py
git commit -m "test: add pytest dev dependency and test skeleton"
```

---

## Task 2: Test and implement quarter/date helpers

These functions do date math only — no DB, no Flask.

**Files:**
- Modify: `src/web/app.py` (add helpers near top, below imports)
- Modify: `src/web/tests/test_helpers.py`

- [ ] **Step 1: Write failing tests for `get_quarter_bounds`**

Append to `src/web/tests/test_helpers.py`:

```python
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
    # Q4 2023 is Oct 1–Dec 31, but data starts 2023-11-09
    start, end = get_quarter_bounds(2023, 4)
    assert start == date(2023, 11, 9)
    assert end == date(2023, 12, 31)


def test_end_does_not_exceed_today():
    # Q3 of a future year should clip end to today
    today = date.today()
    start, end = get_quarter_bounds(today.year, (today.month - 1) // 3 + 1)
    assert end <= today
```

- [ ] **Step 2: Run to confirm failures**

Run from `src/web/`:
```bash
pytest tests/test_helpers.py -v
```
Expected: 6 failures — `ImportError: cannot import name 'get_quarter_bounds' from 'app'`

- [ ] **Step 3: Implement helpers in app.py**

Add after the existing imports in `src/web/app.py`:

```python
import calendar
from datetime import date, timedelta
from flask import request

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
```

- [ ] **Step 4: Run tests to confirm they pass**

Run from `src/web/`:
```bash
pytest tests/test_helpers.py -v
```
Expected: 6 passed

- [ ] **Step 5: Write and run tests for `get_valid_years` and `get_valid_quarters`**

Append to `src/web/tests/test_helpers.py`:

```python
from app import get_valid_years, get_valid_quarters, parse_year_quarter


def test_valid_years_includes_2023_and_current():
    years = get_valid_years()
    assert 2023 in years
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
```

Run from `src/web/`:
```bash
pytest tests/test_helpers.py -v
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/web/app.py src/web/tests/test_helpers.py
git commit -m "feat: add quarter/date helpers with tests"
```

---

## Task 3: Test and implement severity sort and day-map builder

**Files:**
- Modify: `src/web/app.py` (add `sort_rows` and `build_days`)
- Modify: `src/web/tests/test_helpers.py`

- [ ] **Step 1: Write failing tests**

Append to `src/web/tests/test_helpers.py`:

```python
from app import sort_rows, build_days


def test_sort_rows_crucial_first():
    rows = [
        {"severity": "M - Minor", "action": "a"},
        {"severity": "C - Crucial", "action": "b"},
        {"severity": "S - Significant", "action": "c"},
        {"severity": None, "action": "d"},
    ]
    result = sort_rows(rows)
    assert [r["severity"] for r in result] == [
        "C - Crucial", "S - Significant", "M - Minor", None
    ]


def test_sort_rows_na_last():
    rows = [
        {"severity": "NA", "action": "a"},
        {"severity": "M - Minor", "action": "b"},
    ]
    result = sort_rows(rows)
    assert result[0]["severity"] == "M - Minor"
    assert result[1]["severity"] == "NA"


def test_build_days_newest_first():
    rows = [
        {"inspection_date": date(2024, 1, 2), "severity": "M - Minor"},
        {"inspection_date": date(2024, 1, 1), "severity": "C - Crucial"},
    ]
    start = date(2024, 1, 1)
    end = date(2024, 1, 3)
    days = build_days(rows, start, end)
    assert len(days) == 3
    assert days[0][0] == date(2024, 1, 3)
    assert days[1][0] == date(2024, 1, 2)
    assert days[2][0] == date(2024, 1, 1)


def test_build_days_no_data_day_is_empty_list():
    rows = [{"inspection_date": date(2024, 1, 1), "severity": "M - Minor"}]
    start = date(2024, 1, 1)
    end = date(2024, 1, 2)
    days = build_days(rows, start, end)
    assert days[0][0] == date(2024, 1, 2)
    assert days[0][1] == []  # Jan 2 has no data


def test_build_days_rows_sorted_within_day():
    rows = [
        {"inspection_date": date(2024, 1, 1), "severity": "M - Minor"},
        {"inspection_date": date(2024, 1, 1), "severity": "C - Crucial"},
    ]
    start = end = date(2024, 1, 1)
    days = build_days(rows, start, end)
    assert days[0][1][0]["severity"] == "C - Crucial"
    assert days[0][1][1]["severity"] == "M - Minor"
```

- [ ] **Step 2: Run to confirm failures**

Run from `src/web/`:
```bash
pytest tests/test_helpers.py -v -k "sort_rows or build_days"
```
Expected: 5 failures — `ImportError: cannot import name 'sort_rows' from 'app'`

- [ ] **Step 3: Implement `sort_rows` and `build_days` in app.py**

Append to the helpers section in `src/web/app.py` (after `parse_year_quarter`):

```python
def sort_rows(rows):
    return sorted(rows, key=lambda r: SEVERITY_ORDER.get(r.get("severity"), 3))


def build_days(rows, start, end):
    """Return list of (date, sorted_rows) from end to start (newest first)."""
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
```

- [ ] **Step 4: Run all helper tests**

Run from `src/web/`:
```bash
pytest tests/test_helpers.py -v
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add src/web/app.py src/web/tests/test_helpers.py
git commit -m "feat: add severity sort and day-map builder with tests"
```

---

## Task 4: Test and update the Flask route

**Files:**
- Create: `src/web/tests/test_routes.py`
- Modify: `src/web/app.py` (update `index()` route)

- [ ] **Step 1: Write failing route tests**

Create `src/web/tests/test_routes.py`:

```python
import sys
import os
from datetime import date
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module


def _mock_db(rows):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = rows
    return mock_conn


def test_route_returns_200():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert resp.status_code == 200


def test_route_renders_day_boxes():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=2024&q=1")
    assert b"day-box" in resp.data


def test_route_shows_inspection_data():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    rows = [(
        date(2024, 2, 14),   # inspection_date
        "C - Crucial",       # severity
        "Court Order",       # action
        "Rats observed",     # infraction_details
        "Risky Bistro",      # establishment_name
        "1 Main St",         # establishment_address
        "Pass",              # outcome
        "2024-02-20",        # outcome_date
        "500.00",            # amount_fined
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/?year=2024&q=1")
    assert b"Risky Bistro" in resp.data
    assert b"C - Crucial" in resp.data
    assert b"Rats observed" in resp.data


def test_route_invalid_params_returns_200():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=1900&q=99")
    assert resp.status_code == 200


def test_route_no_data_day_shows_no_data_text():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=2024&q=1")
    assert b"No data" in resp.data
```

- [ ] **Step 2: Run to confirm failures**

Run from `src/web/`:
```bash
pytest tests/test_routes.py -v
```
Expected: failures — route still returns flat table HTML, `day-box` not in response

- [ ] **Step 3: Update the Flask route in app.py**

Replace the existing `index()` function in `src/web/app.py`:

```python
@app.route("/")
def index():
    year, q = parse_year_quarter(request.args)
    start, end = get_quarter_bounds(year, q)

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

    return render_template(
        "index.html",
        days=build_days(rows, start, end),
        selected_year=year,
        selected_q=q,
        valid_years=get_valid_years(),
        valid_quarters=get_valid_quarters(year),
    )
```

- [ ] **Step 4: Update the template**

> The route now passes `days`, `selected_year`, `selected_q`, `valid_years`, `valid_quarters` to the template, but the old template references `inspections`. The app returns 500 until the template is updated. Do not run route tests until after this step.

Full replacement of `src/web/templates/index.html`:

Full replacement of `src/web/templates/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DineSafeViz</title>
    <style>
        body { font-family: sans-serif; margin: 2rem; max-width: 1200px; }

        .tabs { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
        .tabs a {
            padding: 0.4rem 1rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
            background: #f5f5f5;
        }
        .tabs a.active {
            background: #333;
            color: #fff;
            border-color: #333;
        }
        .tabs a:hover:not(.active) { background: #e0e0e0; }

        .day-box {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        }
        .day-box h2 {
            margin: 0 0 0.75rem 0;
            font-size: 1rem;
            font-weight: bold;
        }
        .no-data { margin: 0; color: #999; font-style: italic; }

        table { border-collapse: collapse; width: 100%; }
        th, td {
            border: 1px solid #ddd;
            padding: 0.35rem 0.6rem;
            text-align: left;
            font-size: 0.875rem;
        }
        th { background: #f5f5f5; font-weight: 600; white-space: nowrap; }
    </style>
</head>
<body>
    <h1>DineSafe Inspections</h1>

    <div class="tabs">
        {% for y in valid_years %}
        <a href="/?year={{ y }}"
           class="{{ 'active' if y == selected_year else '' }}">{{ y }}</a>
        {% endfor %}
    </div>

    <div class="tabs">
        {% for q in valid_quarters %}
        <a href="/?year={{ selected_year }}&q={{ q }}"
           class="{{ 'active' if q == selected_q else '' }}">Q{{ q }}</a>
        {% endfor %}
    </div>

    {% for day, rows in days %}
    <div class="day-box">
        <h2>{{ day.strftime('%A, %B %-d, %Y') }}</h2>
        {% if rows %}
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Action</th>
                    <th>Infraction Details</th>
                    <th>Establishment Name</th>
                    <th>Address</th>
                    <th>Outcome</th>
                    <th>Outcome Date</th>
                    <th>Amount Fined</th>
                </tr>
            </thead>
            <tbody>
                {% for row in rows %}
                <tr>
                    <td>{{ row.severity or '—' }}</td>
                    <td>{{ row.action or '—' }}</td>
                    <td>{{ row.infraction_details or '—' }}</td>
                    <td>{{ row.establishment_name or '—' }}</td>
                    <td>{{ row.establishment_address or '—' }}</td>
                    <td>{{ row.outcome or '—' }}</td>
                    <td>{{ row.outcome_date or '—' }}</td>
                    <td>{{ row.amount_fined or '—' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p class="no-data">No data</p>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
```

- [ ] **Step 5: Run all tests**

Run from `src/web/`:
```bash
pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 6: Start the app and visually verify**

From the repo root:
```bash
docker compose up --build
```
Then open `http://localhost:5000` in a browser.

Verify:
- Year tabs appear (2023, 2024, 2025, 2026)
- Clicking a year shows Q sub-tabs for that year; 2023 shows only Q4
- Each day has its own rounded box
- Days with data show the 8-column mini-table with rows sorted Crucial → Significant → Minor
- Days without data show "No data"

- [ ] **Step 7: Commit**

```bash
git add src/web/app.py src/web/tests/test_routes.py src/web/templates/index.html
git commit -m "feat: day-grouped inspection display with year/quarter navigation"
```
