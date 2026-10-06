"""DineSafe data loader: initial seed and refresh from local CSVs.

Reads the CSVs that scripts/data.sh mirrors from Azure Blob Storage into
DSV_DATA_DIR. Detects whether the inspections table is empty:
- Empty:     seeds historical (2001-2022) + recent (2023-present) data
- Non-empty: replaces recent data from Dinesafe.csv
"""

import csv
import io
import os
import re

import psycopg2

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DSV_DB_HOST = os.environ.get("DSV_DB_HOST", "dsv-db")
DSV_DB_PORT = os.environ.get("DSV_DB_PORT", "5432")
DSV_DB_NAME = os.environ.get("DSV_DB_NAME", "dinesafe")
DSV_DB_USER = os.environ.get("DSV_DB_USER", "dinesafe")
DSV_DB_PASSWORD = os.environ.get("DSV_DB_PASSWORD", "dinesafe")

# Mirror of the Blob container, written by scripts/data.sh (dsv-data sync).
DSV_DATA_DIR = os.environ.get("DSV_DATA_DIR", "/data")
RECENT_NAME = "Dinesafe.csv"
HISTORICAL_DIR = "dinesafe-historical"
MANIFEST_NAME = "manifest.json"

# Column order for COPY into the inspections table (excludes serial `id`)
INSPECTIONS_COLUMNS = [
    "establishment_id",
    "inspection_id",
    "establishment_name",
    "establishment_type",
    "establishment_address",
    "infraction_details",
    "infraction_category",
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
    "street",
    "unit",
    "postal_code",
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
# "_id", "phone", and "observation" are intentionally absent (discarded on
# import). "oldEstId" is read only by drop_old_id_duplicates and isn't stored,
# because it isn't in INSPECTIONS_COLUMNS. The recent feed no longer carries an
# "actionDesc" column, so `action` stays NULL for recent rows.
RECENT_COLUMN_MAP = {
    "estId": "establishment_id",
    "oldEstId": "old_establishment_id",
    "estName": "establishment_name",
    "address": "establishment_address",
    "typeDesc": "infraction_details",
    "deficiencyDesc": "infraction_category",
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


# Recent-feed addresses end in a postal code or the literal "None".
_POSTAL_RE = re.compile(r"^(?P<rest>.*) (?:(?P<postal>[A-Z]\d[A-Z] \w+)|None)$")
# A unit starts at the first "Word-" token (Unit-, Bldg-, Flr-, Rm-, ...).
# Units without a marker can't be told apart from the street, so they stay in it.
_UNIT_RE = re.compile(r"^(?P<street>[^,]*?),? (?P<unit>[A-Za-z]+-.*)$")


def split_address(address):
    """Split a DineSafe address into (street, unit, postal_code).

    Handles the recent "{street} {unit} {postal}" format (with "None" for
    missing parts) and the historical "{street}, {unit}" format.
    """
    if address is None:
        return None, None, None
    m = _POSTAL_RE.match(address)
    street, postal = (m["rest"], m["postal"]) if m else (address, None)
    street = street.removesuffix(" None")
    u = _UNIT_RE.match(street)
    if u:
        return u["street"], u["unit"], postal
    street, _, unit = street.partition(", ")
    return street, unit or None, postal


def count_unparsed_addresses(rows):
    """Count recent-feed rows whose address doesn't end in a postal code or "None"."""
    return sum(
        1 for r in rows
        if r["establishment_address"] and not _POSTAL_RE.match(r["establishment_address"])
    )


def normalize_date(value):
    """Return an inspection_date string as ISO YYYY-MM-DD.

    Every DineSafe CSV uses YYYY-MM-DD except dinesafe_hist_2023.csv, which
    uses MM/DD/YYYY. Converting to one format keeps string comparisons
    (cutoffs, sorting) correct regardless of source file.
    """
    if value is None or "/" not in value:
        return value
    month, day, year = value.split("/")
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def min_inspection_date(rows):
    """Return the earliest inspection_date string from mapped rows."""
    return min(r["inspection_date"] for r in rows if r["inspection_date"] is not None)


def exclude_on_or_after(rows, cutoff):
    """Return rows whose inspection_date is before cutoff (None dates are kept)."""
    return [r for r in rows if r["inspection_date"] is None or r["inspection_date"] < cutoff]


def drop_old_id_duplicates(rows):
    """Drop recent rows filed under an old establishment ID when the same
    inspection is also listed under the new ID.

    Between Nov 2023 and Nov 2025 the recent feed lists some inspections twice:
    once under the old numeric estId and once under the new estId, whose
    oldEstId points back to the old one. Keeping both double-counts them.
    """
    listed_under_new_id = {
        (r["old_establishment_id"], r["inspection_date"])
        for r in rows
        if r["old_establishment_id"] and r["old_establishment_id"] != r["establishment_id"]
    }
    return [r for r in rows if (r["establishment_id"], r["inspection_date"]) not in listed_under_new_id]


def map_row(row, column_map):
    """Map a CSV row dict to the unified inspections schema using the given column map."""
    mapped = {col: None for col in INSPECTIONS_COLUMNS}
    for csv_col, db_col in column_map.items():
        mapped[db_col] = normalize(row.get(csv_col))
    mapped["inspection_date"] = normalize_date(mapped["inspection_date"])
    mapped["street"], mapped["unit"], mapped["postal_code"] = split_address(mapped["establishment_address"])
    return mapped


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


def decode_csv(raw):
    """Decode DineSafe CSV bytes, tolerating either UTF-8 or Windows-1252.

    DineSafe exports mix encodings across files (older years are UTF-8 with a BOM,
    newer files are Windows-1252), so decode UTF-8 first and fall back to cp1252.
    """
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def _read_csv_rows(csv_path, column_map):
    """Read a DineSafe CSV file into mapped rows."""
    with open(csv_path, "rb") as f:
        text = decode_csv(f.read())
    reader = csv.DictReader(io.StringIO(text))
    return [map_row(r, column_map) for r in reader]


def require_manifest(data_dir):
    """Exit with a clear message unless data_dir holds a synced mirror."""
    if not os.path.isfile(os.path.join(data_dir, MANIFEST_NAME)):
        raise SystemExit(
            f"{data_dir}/{MANIFEST_NAME} is missing. Run scripts/data.sh to "
            "sync the CSVs from Azure Blob Storage first."
        )


def _insert_historical_csv(conn, csv_path, name, cutoff):
    """Parse one historical CSV file and bulk-insert its rows.

    Drops rows on or after cutoff: newer historical archives now extend into
    the recent CSV's date window (for example a 2023 historical file
    alongside a recent feed that also starts in 2023), and inserting both
    would double-count the overlapping inspections.
    """
    rows = _read_csv_rows(csv_path, HISTORICAL_COLUMN_MAP)
    rows = exclude_on_or_after(rows, cutoff)
    bulk_insert(conn, rows)
    print(f"  Loaded {name}: {len(rows)} rows")


def load_historical(conn, cutoff, data_dir):
    """Load every historical CSV under data_dir/dinesafe-historical.

    cutoff is the earliest inspection_date in the recent CSV; historical
    rows on or after it are skipped to avoid double-counting.
    """
    csv_dir = os.path.join(data_dir, HISTORICAL_DIR)
    print(f"Reading historical data from {csv_dir} ...")
    for name in sorted(os.listdir(csv_dir)):
        if name.endswith(".csv"):
            _insert_historical_csv(conn, os.path.join(csv_dir, name), name, cutoff)


def _read_recent_rows(data_dir):
    """Return parsed, de-duplicated recent rows from data_dir/Dinesafe.csv."""
    source = os.path.join(data_dir, RECENT_NAME)
    print(f"Reading recent data from {source} ...")
    rows = _read_csv_rows(source, RECENT_COLUMN_MAP)
    deduped = drop_old_id_duplicates(rows)
    print(f"  Dropped old-ID duplicate rows: {len(rows) - len(deduped)}")
    rows = deduped
    # Non-zero means the upstream address format changed; the raw address is kept in street.
    print(f"  Unparsed recent addresses: {count_unparsed_addresses(rows)}")
    return rows


def seed(conn):
    """Full seed: load recent data, then historical data excluding the
    recent CSV's date window, so overlapping inspections aren't
    double-counted. Commits once.
    """
    recent_rows = _read_recent_rows(DSV_DATA_DIR)
    cutoff = min_inspection_date(recent_rows)
    load_historical(conn, cutoff, DSV_DATA_DIR)
    bulk_insert(conn, recent_rows)
    print(f"  Loaded recent CSV: {len(recent_rows)} rows")
    conn.commit()
    print("Seed complete.")


# ---------------------------------------------------------------------------
# Refresh path — business-day timer, table already has data
# ---------------------------------------------------------------------------


def refresh(conn):
    """Replace all recent data in a single transaction.

    Reads the CSV first, then deletes + inserts inside one
    transaction so the table is never in a partial state.
    The delete cutoff is derived from the earliest date in the
    fresh CSV so it tracks the upstream data window automatically.
    """
    rows = _read_recent_rows(DSV_DATA_DIR)
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
    require_manifest(DSV_DATA_DIR)
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
