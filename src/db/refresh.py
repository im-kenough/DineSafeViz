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
