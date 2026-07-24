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
# Configuration
# ---------------------------------------------------------------------------

RECENT_CSV_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/"
    "af0f5b8a-4b73-4a50-8781-65e949792b40/download/dinesafe.csv"
)

HISTORICAL_ZIP_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/"
    "c0a5f6b0-534a-47c3-867d-d4b5cc84a656/download/"
    "Dinesafe%20Historical%20Data.zip"
)

DSV_DB_HOST = os.environ.get("DSV_DB_HOST", "dsv-db")
DSV_DB_PORT = os.environ.get("DSV_DB_PORT", "5432")
DSV_DB_NAME = os.environ.get("DSV_DB_NAME", "dinesafe")
DSV_DB_USER = os.environ.get("DSV_DB_USER", "dinesafe")
DSV_DB_PASSWORD = os.environ.get("DSV_DB_PASSWORD", "dinesafe")

# When set, seed from local CSVs under this directory instead of downloading
# from the Toronto Open Data portal. Used for offline/reproducible local
# testing. Unset (the default) preserves the live-download behavior.
DSV_LOCAL_DATA_DIR = os.environ.get("DSV_LOCAL_DATA_DIR", "").strip()

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
# "_id", "oldEstId", "phone", and "observation" are intentionally absent
# (discarded on import). The recent feed no longer carries an "actionDesc"
# column, so `action` stays NULL for recent rows.
RECENT_COLUMN_MAP = {
    "estId": "establishment_id",
    "estName": "establishment_name",
    "address": "establishment_address",
    "typeDesc": "infraction_details",
    "deficiencyDesc": "inspection_observation",
    "inspectionDate": "inspection_date",
    "inspectionStatus": "establishment_status",
    "severity": "severity",
    "OutcomeDesc": "outcome",
    "OutcomeDate": "outcome_date",
    "amountFined": "amount_fined",
    "latitude": "latitude",
    "longitude": "longitude",
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


def min_inspection_date(rows):
    """Return the earliest inspection_date string from mapped rows."""
    return min(r["inspection_date"] for r in rows if r["inspection_date"] is not None)


def map_row(row, column_map):
    """Map a CSV row dict to the unified inspections schema using the given column map."""
    mapped = {col: None for col in INSPECTIONS_COLUMNS}
    for csv_col, db_col in column_map.items():
        mapped[db_col] = normalize(row.get(csv_col))
    return mapped


def recent_source(local_dir):
    """Return the recent CSV source: a local file path if local_dir is set, else the live URL."""
    if local_dir:
        return os.path.join(local_dir, "Dinesafe.csv")
    return RECENT_CSV_URL


def historical_source(local_dir):
    """Return the local historical CSV directory if local_dir is set, else None (use the live ZIP)."""
    if local_dir:
        return os.path.join(local_dir, "dinesafe-historical")
    return None


# ---------------------------------------------------------------------------
# Database utilities
# ---------------------------------------------------------------------------


def get_connection():
    """Return a psycopg2 connection using the module-level config."""
    return psycopg2.connect(
        host=DSV_DB_HOST,
        port=DSV_DB_PORT,
        dbname=DSV_DB_NAME,
        user=DSV_DB_USER,
        password=DSV_DB_PASSWORD,
    )


def is_empty(conn):
    """Return True if the inspections table has zero rows."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM inspections LIMIT 1")
        return cur.fetchone() is None


def bulk_insert(conn, rows):
    """Insert mapped row dicts into inspections via COPY for speed.

    Uses a tab-separated StringIO buffer. None values become \\N
    (Postgres COPY null marker). Tabs, carriage returns, and newlines
    in data values are replaced with spaces to avoid COPY format errors.
    """
    if not rows:
        return
    buf = io.StringIO()
    for row in rows:
        line = "\t".join(
            "\\N" if row[col] is None
            else str(row[col]).replace("\t", " ").replace("\r", " ").replace("\n", " ")
            for col in INSPECTIONS_COLUMNS
        )
        buf.write(line + "\n")
    buf.seek(0)
    with conn.cursor() as cur:
        cur.copy_from(buf, "inspections", columns=INSPECTIONS_COLUMNS)


# ---------------------------------------------------------------------------
# Seed path — first deploy, table is empty
# ---------------------------------------------------------------------------


def _read_csv_rows(csv_path, column_map):
    """Read a DineSafe CSV into mapped rows, tolerating either UTF-8 or Windows-1252.

    DineSafe exports mix encodings across files (older years are UTF-8 with a BOM,
    newer files are Windows-1252), so decode UTF-8 first and fall back to cp1252.
    """
    with open(csv_path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    reader = csv.DictReader(io.StringIO(text))
    return [map_row(r, column_map) for r in reader]


def _insert_historical_csv(conn, csv_path, name):
    """Parse one historical CSV file and bulk-insert its rows."""
    rows = _read_csv_rows(csv_path, HISTORICAL_COLUMN_MAP)
    bulk_insert(conn, rows)
    print(f"  Loaded {name}: {len(rows)} rows")


def download_and_load_historical(conn):
    """Load all historical CSVs from the local directory or the live ZIP."""
    local_dir = historical_source(DSV_LOCAL_DATA_DIR)
    if local_dir:
        print(f"Reading historical data from {local_dir} ...")
        for name in sorted(os.listdir(local_dir)):
            if not name.endswith(".csv"):
                continue
            _insert_historical_csv(conn, os.path.join(local_dir, name), name)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "historical.zip")
        print(f"Downloading historical data from {HISTORICAL_ZIP_URL} ...")
        urlretrieve(HISTORICAL_ZIP_URL, zip_path)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)
            for name in sorted(zf.namelist()):
                if not name.endswith(".csv"):
                    continue
                _insert_historical_csv(conn, os.path.join(tmpdir, name), name)


def _read_recent_csv(csv_path):
    """Parse the recent Dinesafe CSV file into mapped rows."""
    return _read_csv_rows(csv_path, RECENT_COLUMN_MAP)


def _fetch_recent_rows():
    """Return parsed recent rows from the local file or a live download."""
    source = recent_source(DSV_LOCAL_DATA_DIR)
    if DSV_LOCAL_DATA_DIR:
        print(f"Reading recent data from {source} ...")
        return _read_recent_csv(source)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "recent.csv")
        print(f"Downloading recent data from {source} ...")
        urlretrieve(source, tmp_path)
        return _read_recent_csv(tmp_path)


def download_and_load_recent(conn):
    """Download the recent Dinesafe CSV and insert all rows."""
    rows = _fetch_recent_rows()
    bulk_insert(conn, rows)
    print(f"  Loaded recent CSV: {len(rows)} rows")


def seed(conn):
    """Full seed: load historical data then recent data. Commits once."""
    download_and_load_historical(conn)
    download_and_load_recent(conn)
    conn.commit()
    print("Seed complete.")


# ---------------------------------------------------------------------------
# Refresh path — daily cron, table already has data
# ---------------------------------------------------------------------------


def refresh(conn):
    """Replace all recent data in a single transaction.

    Downloads the CSV first, then deletes + inserts inside one
    transaction so the table is never in a partial state.
    The delete cutoff is derived from the earliest date in the
    fresh CSV so it tracks the upstream data window automatically.
    """
    rows = _fetch_recent_rows()
    cutoff = min_inspection_date(rows)
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM inspections WHERE inspection_date >= %s",
            (cutoff,),
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
