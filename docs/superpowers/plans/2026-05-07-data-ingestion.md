# Data Ingestion Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static CSV-mount seeding with a Python script that loads all historical data (2001–2022) plus recent data (2023–present) into Postgres, with daily cron refresh.

**Architecture:** `init.sql` creates the schema only. `src/db/refresh.py` auto-detects an empty table and either seeds (historical ZIP + recent CSV) or refreshes (delete recent rows + re-insert from fresh download). All config values are centralized constants.

**Tech Stack:** Python 3, psycopg2, stdlib csv/zipfile/urllib/tempfile, Postgres 17

**Spec:** `docs/superpowers/specs/2026-05-07-data-ingestion-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/db/init.sql` | Modify | Schema-only: create `inspections` table with 2 new columns, no data loading |
| `src/db/refresh.py` | Create | Config, column mapping, download, seed, daily refresh, CLI entrypoint |
| `src/db/requirements.txt` | Create | psycopg2-binary dependency for refresh script |
| `src/db/tests/test_refresh.py` | Create | Unit tests for pure functions (normalize, column mapping) |
| `src/web/app.py` | Modify | Update `DATA_START` and `get_valid_years()` for 2001–present |
| `src/web/tests/test_helpers.py` | Modify | Fix tests affected by new DATA_START |
| `docker-compose.yml` | Modify | Remove CSV volume mount |
| `docs/ref/data.md` | Modify | Document unified schema with new columns |

---

### Task 1: Update init.sql to schema-only

`init.sql` currently creates a staging table, COPYs the CSV, transforms data, and drops staging. After this task it only creates the `inspections` table with two new columns.

**Files:**
- Modify: `src/db/init.sql`

- [ ] **Step 1: Replace init.sql contents**

Replace the entire file with:

```sql
CREATE TABLE inspections (
    id                          SERIAL PRIMARY KEY,
    establishment_id            TEXT,
    inspection_id               TEXT,
    establishment_name          TEXT,
    establishment_type          TEXT,
    establishment_address       TEXT,
    infraction_details          TEXT,
    inspection_observation      TEXT,
    inspection_date             DATE,
    severity                    TEXT,
    action                      TEXT,
    outcome                     TEXT,
    outcome_date                TEXT,
    amount_fined                TEXT,
    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
    unique_id                   TEXT,
    establishment_status        TEXT,
    min_inspections_per_year    TEXT
);
```

That is the complete file. The staging table (`_csv_staging`), `COPY` command, `INSERT ... SELECT` transform, and `DROP TABLE _csv_staging` are all removed.

- [ ] **Step 2: Commit**

```bash
git add src/db/init.sql
git commit -m "refactor: make init.sql schema-only, add historical columns

Add establishment_status and min_inspections_per_year columns for
historical data. Remove staging table, COPY, and data transform —
all data loading moves to refresh.py."
```

---

### Task 2: Create refresh.py — config and column mapping with tests

Build the pure-function layer: configuration constants, value normalization, and column mapping for both CSV formats. Test-driven.

**Files:**
- Create: `src/db/refresh.py`
- Create: `src/db/tests/__init__.py`
- Create: `src/db/tests/test_refresh.py`
- Create: `src/db/requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
psycopg2-binary==2.9.12
```

- [ ] **Step 2: Create empty test package**

Create `src/db/tests/__init__.py` as an empty file.

- [ ] **Step 3: Write failing tests for normalize and column mapping**

Create `src/db/tests/test_refresh.py`:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from refresh import (
    normalize,
    map_historical_row,
    map_recent_row,
    INSPECTIONS_COLUMNS,
)


class TestNormalize:
    def test_none_string_returns_none(self):
        assert normalize("None") is None

    def test_empty_string_returns_none(self):
        assert normalize("") is None

    def test_regular_value_unchanged(self):
        assert normalize("Pass") == "Pass"

    def test_whitespace_only_preserved(self):
        assert normalize("  ") == "  "


class TestMapHistoricalRow:
    SAMPLE_ROW = {
        "Rec #": "1",
        "Establishment ID": "10500438",
        "Inspection ID": "103743023",
        "Establishment Name": "1 PLUS 1 PIZZA",
        "Establishment Type": "Food Take Out",
        "Establishment Address": "361 OAKWOOD AVE",
        "Latitude": "43.68725",
        "Longitude": "-79.43842",
        "Establishment Status": "Pass",
        "Min. Inspections Per Year": "2",
        "Infraction Details": "",
        "Inspection Date": "2016-06-03",
        "Severity": "",
        "Action": "",
        "Outcome": "",
        "Amount Fined": "",
    }

    def test_maps_establishment_id(self):
        result = map_historical_row(self.SAMPLE_ROW)
        assert result["establishment_id"] == "10500438"

    def test_discards_rec_number(self):
        result = map_historical_row(self.SAMPLE_ROW)
        assert "Rec #" not in result

    def test_maps_historical_only_columns(self):
        result = map_historical_row(self.SAMPLE_ROW)
        assert result["establishment_status"] == "Pass"
        assert result["min_inspections_per_year"] == "2"

    def test_recent_only_columns_are_none(self):
        result = map_historical_row(self.SAMPLE_ROW)
        assert result["inspection_observation"] is None
        assert result["outcome_date"] is None
        assert result["unique_id"] is None

    def test_empty_values_become_none(self):
        result = map_historical_row(self.SAMPLE_ROW)
        assert result["infraction_details"] is None
        assert result["severity"] is None
        assert result["action"] is None

    def test_all_inspections_columns_present(self):
        result = map_historical_row(self.SAMPLE_ROW)
        for col in INSPECTIONS_COLUMNS:
            assert col in result, f"Missing column: {col}"


class TestMapRecentRow:
    SAMPLE_ROW = {
        "_id": "1",
        "Establishment ID": "10752656",
        "Inspection ID": "None",
        "Establishment Name": "HASHTAG INDIA RESTAURANT",
        "Establishment Type": "Food Take Out",
        "Establishment Address": "1871 O'CONNOR DR None M4A 1X1",
        "Infraction Details": "FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED",
        "Inspection Observation": "One or more minor infractions",
        "Inspection Date": "2024-03-06",
        "Severity": "M - Minor",
        "Action": "Notice to Comply",
        "Outcome": "None",
        "Outcome Date": "",
        "Amount Fined": "",
        "Latitude": "43.72199",
        "Longitude": "-79.30349",
        "unique_id": "168f86274045194142c0e7c381ccb75d",
    }

    def test_maps_establishment_id(self):
        result = map_recent_row(self.SAMPLE_ROW)
        assert result["establishment_id"] == "10752656"

    def test_discards_id(self):
        result = map_recent_row(self.SAMPLE_ROW)
        assert "_id" not in result

    def test_maps_recent_only_columns(self):
        result = map_recent_row(self.SAMPLE_ROW)
        assert result["inspection_observation"] == "One or more minor infractions"
        assert result["unique_id"] == "168f86274045194142c0e7c381ccb75d"

    def test_historical_only_columns_are_none(self):
        result = map_recent_row(self.SAMPLE_ROW)
        assert result["establishment_status"] is None
        assert result["min_inspections_per_year"] is None

    def test_none_string_becomes_none(self):
        result = map_recent_row(self.SAMPLE_ROW)
        assert result["inspection_id"] is None
        assert result["outcome"] is None

    def test_all_inspections_columns_present(self):
        result = map_recent_row(self.SAMPLE_ROW)
        for col in INSPECTIONS_COLUMNS:
            assert col in result, f"Missing column: {col}"
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd /home/sam/SCM/github/DineSafeViz && python -m pytest src/db/tests/test_refresh.py -v`

Expected: ImportError — `refresh` module does not exist yet.

- [ ] **Step 5: Create refresh.py with config and mapping functions**

Create `src/db/refresh.py`:

```python
"""DineSafe data ingestion: initial seed and daily refresh.

Detects whether the inspections table is empty:
- Empty:     seeds historical (2001-2022) + recent (2023-present) data
- Non-empty: replaces recent data from Toronto Open Data daily CSV
"""

import csv
import io
import os
import tempfile
import zipfile
from urllib.request import urlretrieve

import psycopg2

# ---------------------------------------------------------------------------
# Configuration — future: move to a config file
# ---------------------------------------------------------------------------

CKAN_BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca"

RECENT_CSV_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/"
    "eda39233-4791-464e-98e6-094f51a01916/download/Dinesafe.csv"
)

HISTORICAL_ZIP_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/"
    "c0a5f6b0-534a-47c3-867d-d4b5cc84a656/download/"
    "Dinesafe%20Historical%20Data.zip"
)

RECENT_DATA_START_DATE = "2023-11-01"

HISTORICAL_FILE_PATTERN = "dinesafe_hist_{year}.csv"

DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "dinesafe")
DB_USER = os.environ.get("DB_USER", "dinesafe")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "dinesafe")

# Column order for COPY into the inspections table (excludes serial `id`)
INSPECTIONS_COLUMNS = [
    "establishment_id",
    "inspection_id",
    "establishment_name",
    "establishment_type",
    "establishment_address",
    "infraction_details",
    "inspection_observation",
    "inspection_date",
    "severity",
    "action",
    "outcome",
    "outcome_date",
    "amount_fined",
    "latitude",
    "longitude",
    "unique_id",
    "establishment_status",
    "min_inspections_per_year",
]

# Maps historical CSV headers → unified inspections column names.
# "Rec #" is intentionally absent (discarded on import).
HISTORICAL_COLUMN_MAP = {
    "Establishment ID": "establishment_id",
    "Inspection ID": "inspection_id",
    "Establishment Name": "establishment_name",
    "Establishment Type": "establishment_type",
    "Establishment Address": "establishment_address",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Establishment Status": "establishment_status",
    "Min. Inspections Per Year": "min_inspections_per_year",
    "Infraction Details": "infraction_details",
    "Inspection Date": "inspection_date",
    "Severity": "severity",
    "Action": "action",
    "Outcome": "outcome",
    "Amount Fined": "amount_fined",
}

# Maps recent CSV headers → unified inspections column names.
# "_id" is intentionally absent (discarded on import).
RECENT_COLUMN_MAP = {
    "Establishment ID": "establishment_id",
    "Inspection ID": "inspection_id",
    "Establishment Name": "establishment_name",
    "Establishment Type": "establishment_type",
    "Establishment Address": "establishment_address",
    "Infraction Details": "infraction_details",
    "Inspection Observation": "inspection_observation",
    "Inspection Date": "inspection_date",
    "Severity": "severity",
    "Action": "action",
    "Outcome": "outcome",
    "Outcome Date": "outcome_date",
    "Amount Fined": "amount_fined",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "unique_id": "unique_id",
}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def normalize(value):
    """Convert the string 'None' and empty strings to Python None."""
    if value in ("None", ""):
        return None
    return value


def map_historical_row(row):
    """Map a historical CSV row dict to the unified inspections schema."""
    mapped = {col: None for col in INSPECTIONS_COLUMNS}
    for csv_col, db_col in HISTORICAL_COLUMN_MAP.items():
        mapped[db_col] = normalize(row.get(csv_col))
    return mapped


def map_recent_row(row):
    """Map a recent CSV row dict to the unified inspections schema."""
    mapped = {col: None for col in INSPECTIONS_COLUMNS}
    for csv_col, db_col in RECENT_COLUMN_MAP.items():
        mapped[db_col] = normalize(row.get(csv_col))
    return mapped
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /home/sam/SCM/github/DineSafeViz && python -m pytest src/db/tests/test_refresh.py -v`

Expected: all 16 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/db/refresh.py src/db/tests/__init__.py src/db/tests/test_refresh.py src/db/requirements.txt
git commit -m "feat: add refresh.py config, normalize, and column mapping

Pure-function layer for data ingestion. Maps both the 16-column
historical CSV schema and the 17-column recent CSV schema to the
unified inspections table."
```

---

### Task 3: Add DB utilities and bulk insert to refresh.py

Add `get_connection()`, `is_empty()`, and `bulk_insert()` to refresh.py.

**Files:**
- Modify: `src/db/refresh.py`

- [ ] **Step 1: Add DB utility functions**

Append to the end of `src/db/refresh.py`:

```python
# ---------------------------------------------------------------------------
# Database utilities
# ---------------------------------------------------------------------------


def get_connection():
    """Return a psycopg2 connection using the module-level config."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def is_empty(conn):
    """Return True if the inspections table has zero rows."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM inspections")
        return cur.fetchone()[0] == 0


def bulk_insert(conn, rows):
    """Insert mapped row dicts into inspections via COPY for speed.

    Uses a tab-separated StringIO buffer. None values become \\N
    (Postgres COPY null marker). Tabs in data values are replaced
    with spaces to avoid column-delimiter collisions.
    """
    if not rows:
        return
    buf = io.StringIO()
    for row in rows:
        line = "\t".join(
            "\\N" if row[col] is None else str(row[col]).replace("\t", " ")
            for col in INSPECTIONS_COLUMNS
        )
        buf.write(line + "\n")
    buf.seek(0)
    with conn.cursor() as cur:
        cur.copy_from(buf, "inspections", columns=INSPECTIONS_COLUMNS)
```

- [ ] **Step 2: Commit**

```bash
git add src/db/refresh.py
git commit -m "feat: add DB connection, is_empty, and bulk_insert to refresh.py"
```

---

### Task 4: Add seed path to refresh.py

Download the historical ZIP + recent CSV and load everything on first deploy.

**Files:**
- Modify: `src/db/refresh.py`

- [ ] **Step 1: Add seed functions**

Append to the end of `src/db/refresh.py`:

```python
# ---------------------------------------------------------------------------
# Seed path — first deploy, table is empty
# ---------------------------------------------------------------------------


def download_and_load_historical(conn):
    """Download the historical ZIP and insert all CSVs (2001-2022)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "historical.zip")
        print(f"Downloading historical data from {HISTORICAL_ZIP_URL} ...")
        urlretrieve(HISTORICAL_ZIP_URL, zip_path)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)
            for name in sorted(zf.namelist()):
                if not name.endswith(".csv"):
                    continue
                csv_path = os.path.join(tmpdir, name)
                with open(csv_path, newline="", encoding="utf-8-sig") as f:
                    rows = [map_historical_row(r) for r in csv.DictReader(f)]
                bulk_insert(conn, rows)
                print(f"  Loaded {name}: {len(rows)} rows")


def download_and_load_recent(conn):
    """Download the recent Dinesafe CSV and insert all rows."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        print(f"Downloading recent data from {RECENT_CSV_URL} ...")
        urlretrieve(RECENT_CSV_URL, tmp_path)
        with open(tmp_path, newline="", encoding="utf-8-sig") as f:
            rows = [map_recent_row(r) for r in csv.DictReader(f)]
        bulk_insert(conn, rows)
        print(f"  Loaded recent CSV: {len(rows)} rows")
    finally:
        os.unlink(tmp_path)


def seed(conn):
    """Full seed: load historical data then recent data. Commits once."""
    download_and_load_historical(conn)
    download_and_load_recent(conn)
    conn.commit()
    print("Seed complete.")
```

- [ ] **Step 2: Commit**

```bash
git add src/db/refresh.py
git commit -m "feat: add seed path — download historical ZIP + recent CSV"
```

---

### Task 5: Add refresh path and main entrypoint to refresh.py

Daily refresh: delete recent rows and re-insert from fresh download, all in one transaction.

**Files:**
- Modify: `src/db/refresh.py`

- [ ] **Step 1: Add refresh function and main entrypoint**

Append to the end of `src/db/refresh.py`:

```python
# ---------------------------------------------------------------------------
# Refresh path — daily cron, table already has data
# ---------------------------------------------------------------------------


def refresh(conn):
    """Replace all recent data in a single transaction.

    Downloads the CSV first, then deletes + inserts inside one
    transaction so the table is never in a partial state.
    """
    # Download and parse before touching the DB
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        print(f"Downloading recent data from {RECENT_CSV_URL} ...")
        urlretrieve(RECENT_CSV_URL, tmp_path)
        with open(tmp_path, newline="", encoding="utf-8-sig") as f:
            rows = [map_recent_row(r) for r in csv.DictReader(f)]
    finally:
        os.unlink(tmp_path)

    # Single transaction: delete stale rows, insert fresh ones
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM inspections WHERE inspection_date >= %s",
            (RECENT_DATA_START_DATE,),
        )
        deleted = cur.rowcount
    bulk_insert(conn, rows)
    conn.commit()
    print(f"Refresh complete: deleted {deleted}, inserted {len(rows)} rows.")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main():
    conn = get_connection()
    try:
        if is_empty(conn):
            print("Table is empty — running full seed...")
            seed(conn)
        else:
            print("Table has data — running daily refresh...")
            refresh(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/db/refresh.py
git commit -m "feat: add daily refresh path and CLI entrypoint to refresh.py"
```

---

### Task 6: Update app.py and fix affected tests

Change `DATA_START` and `get_valid_years()` to cover 2001–present. Fix the two tests that depend on the old values.

**Files:**
- Modify: `src/web/app.py:17,53`
- Modify: `src/web/tests/test_helpers.py:34-38,51-53`

- [ ] **Step 1: Run existing tests to confirm green baseline**

Run: `cd /home/sam/SCM/github/DineSafeViz && python -m pytest src/web/tests/ -v`

Expected: all tests PASS.

- [ ] **Step 2: Update app.py**

In `src/web/app.py`, make two changes:

Change line 17:
```python
# Before
DATA_START = date(2023, 11, 9)
# After
DATA_START = date(2001, 1, 1)
```

Change line 53 (inside `get_valid_years()`):
```python
# Before
return list(range(2023, date.today().year + 1))
# After
return list(range(2001, date.today().year + 1))
```

- [ ] **Step 3: Run tests to see what breaks**

Run: `cd /home/sam/SCM/github/DineSafeViz && python -m pytest src/web/tests/test_helpers.py -v`

Expected failures:
- `test_q4_2023_clips_to_data_start` — start is now `date(2023, 10, 1)` instead of `date(2023, 11, 9)`

- [ ] **Step 4: Fix test_q4_2023_clips_to_data_start**

In `src/web/tests/test_helpers.py`, update the test. The Q4 2023 start date is no longer clipped by DATA_START (which is now 2001-01-01), so it becomes the natural Q4 start: Oct 1.

```python
# Before
def test_q4_2023_clips_to_data_start():
    # Q4 2023 is Oct 1–Dec 31, but data starts 2023-11-09
    start, end = get_quarter_bounds(2023, 4)
    assert start == date(2023, 11, 9)
    assert end == date(2023, 12, 31)

# After
def test_q4_2023_clips_to_data_start():
    # Q4 2023 is Oct 1–Dec 31; DATA_START (2001-01-01) no longer clips
    start, end = get_quarter_bounds(2023, 4)
    assert start == date(2023, 10, 1)
    assert end == date(2023, 12, 31)
```

- [ ] **Step 5: Update test_valid_years to cover 2001**

In `src/web/tests/test_helpers.py`, update the existing test:

```python
# Before
def test_valid_years_includes_2023_and_current():
    years = get_valid_years()
    assert 2023 in years
    assert date.today().year in years

# After
def test_valid_years_includes_2001_and_current():
    years = get_valid_years()
    assert 2001 in years
    assert date.today().year in years
```

- [ ] **Step 6: Run all tests to confirm green**

Run: `cd /home/sam/SCM/github/DineSafeViz && python -m pytest src/web/tests/ -v`

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/web/app.py src/web/tests/test_helpers.py
git commit -m "feat: extend data range to 2001-present

Update DATA_START and get_valid_years() to cover historical data.
Fix tests for new date boundaries."
```

---

### Task 7: Update docker-compose.yml

Remove the CSV volume mount that is no longer needed.

**Files:**
- Modify: `docker-compose.yml:11`

- [ ] **Step 1: Remove the Dinesafe.csv volume mount**

In `docker-compose.yml`, in the `db` service `volumes` section, remove the line:

```yaml
      - ./src/db/Dinesafe.csv:/data/Dinesafe.csv
```

Keep the other two volume entries (`pgdata` and `init.sql`).

The `volumes` section for `db` should now be:

```yaml
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./src/db/init.sql:/docker-entrypoint-initdb.d/init.sql
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: remove static CSV volume mount from db service

Data loading is now handled by refresh.py, not init.sql COPY."
```

---

### Task 8: Update docs/ref/data.md

Document the unified schema with the two new columns and the ingestion workflow.

**Files:**
- Modify: `docs/ref/data.md`

- [ ] **Step 1: Read current data.md**

Read `docs/ref/data.md` to confirm current contents before editing.

- [ ] **Step 2: Add unified schema section**

After the existing "Historical data (2001-2015)" section (which ends around line 240), append a new section:

```markdown
# Unified schema (inspections table)

The Postgres `inspections` table merges both historical (2001–2022)
and recent (2023–present) data into a single schema. Two columns from
the historical dataset are preserved; columns absent in a given era
are NULL.

| # | Column                     | Type             | Historical (2001–2022) | Recent (2023–present) |
|---|----------------------------|------------------|------------------------|-----------------------|
| 1 | id                         | SERIAL (PK)      | auto-generated         | auto-generated        |
| 2 | establishment_id           | TEXT             | populated              | populated             |
| 3 | inspection_id              | TEXT             | populated              | populated             |
| 4 | establishment_name         | TEXT             | populated              | populated             |
| 5 | establishment_type         | TEXT             | populated              | populated             |
| 6 | establishment_address      | TEXT             | populated              | populated             |
| 7 | infraction_details         | TEXT             | populated              | populated             |
| 8 | inspection_observation     | TEXT             | NULL                   | populated             |
| 9 | inspection_date            | DATE             | populated              | populated             |
| 10| severity                   | TEXT             | populated              | populated             |
| 11| action                     | TEXT             | populated              | populated             |
| 12| outcome                    | TEXT             | populated              | populated             |
| 13| outcome_date               | TEXT             | NULL                   | populated             |
| 14| amount_fined               | TEXT             | populated              | populated             |
| 15| latitude                   | DOUBLE PRECISION | populated              | populated             |
| 16| longitude                  | DOUBLE PRECISION | populated              | populated             |
| 17| unique_id                  | TEXT             | NULL                   | populated             |
| 18| establishment_status       | TEXT             | populated              | NULL                  |
| 19| min_inspections_per_year   | TEXT             | populated              | NULL                  |

## Data ingestion

Data loading is handled by `src/db/refresh.py`, not by `init.sql`.

**Initial seed (empty table):**
1. Downloads the historical ZIP (2001–2022 CSVs)
2. Downloads the recent Dinesafe.csv (2023–present)
3. Inserts both into the `inspections` table in a single transaction

**Daily refresh (table has data):**
1. Downloads the recent Dinesafe.csv
2. Deletes all rows with `inspection_date >= 2023-11-01`
3. Inserts the fresh CSV rows
4. All within a single transaction

**Cron example:**
```
0 6 * * * cd /path/to/DineSafeViz && python3 src/db/refresh.py
```
```

- [ ] **Step 3: Commit**

```bash
git add docs/ref/data.md
git commit -m "docs: add unified schema and ingestion workflow to data.md"
```
