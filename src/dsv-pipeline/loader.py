"""DineSafe data loader: transforms and the seed and refresh SQL.

pipeline.py downloads the raw-zone files into a temp directory, then calls
seed() or refresh() with their paths. Rows stream from each CSV into COPY,
so memory holds one batch, not a file. Neither commits: pipeline.py records
the load in load_log and commits once, so the data and its log row land
together.
"""

import codecs
import csv
import io
import itertools
import os
import re
from typing import NamedTuple

import psycopg2

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DSV_DB_HOST = os.environ.get("DSV_DB_HOST", "dsv-db")
DSV_DB_PORT = os.environ.get("DSV_DB_PORT", "5432")
DSV_DB_NAME = os.environ.get("DSV_DB_NAME", "dinesafe")
DSV_DB_USER = os.environ.get("DSV_DB_USER", "dinesafe")
DSV_DB_PASSWORD = os.environ.get("DSV_DB_PASSWORD", "dinesafe")

RECENT_NAME = "Dinesafe.csv"

# Rows per COPY. Bounds memory; the whole load is still one transaction.
COPY_BATCH = 10000

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
# import). "oldEstId" is read only by scan_recent and isn't stored: bulk_insert
# writes only INSPECTIONS_COLUMNS. The recent feed no longer carries an
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


def exclude_on_or_after(rows, cutoff):
    """Yield rows whose inspection_date is before cutoff (None dates are kept)."""
    return (r for r in rows if r["inspection_date"] is None or r["inspection_date"] < cutoff)


def drop_old_id_duplicates(rows, keys):
    """Drop recent rows filed under an old establishment ID when the same
    inspection is also listed under the new ID.

    Between Nov 2023 and Nov 2025 the recent feed lists some inspections twice:
    once under the old numeric estId and once under the new estId, whose
    oldEstId points back to the old one. Keeping both double-counts them.
    keys holds the (old ID, date) pairs listed under a new ID; scan_recent
    collects them in a first pass, so this pass can stream.
    """
    return (r for r in rows if (r["establishment_id"], r["inspection_date"]) not in keys)


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


def _copy_escape(value):
    """Escape a value for COPY's text format: double backslashes, which COPY
    reads as escapes, and turn tabs, carriage returns, and newlines into
    spaces. Chained replace() is several times faster here than
    str.translate with a dict table, which runs once per field per row.
    """
    return value.replace("\\", "\\\\").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def bulk_insert(conn, rows):
    """Insert mapped row dicts into inspections via COPY, COPY_BATCH at a time.

    Takes any iterable, so rows can stream from a CSV. Each batch is a
    tab-separated StringIO buffer in COPY's text format. None values become
    \\N (the null marker), and the rest go through _copy_escape. Returns the
    row count.
    """
    inserted = 0
    with conn.cursor() as cur:
        for batch in itertools.batched(rows, COPY_BATCH, strict=False):
            buf = io.StringIO()
            for row in batch:
                line = "\t".join(
                    "\\N" if row[col] is None else _copy_escape(str(row[col]))
                    for col in INSPECTIONS_COLUMNS
                )
                buf.write(line + "\n")
            buf.seek(0)
            cur.copy_from(buf, "inspections", columns=INSPECTIONS_COLUMNS)
            inserted += len(batch)
    return inserted


# ---------------------------------------------------------------------------
# Seed and refresh — called by pipeline.py, which commits
# ---------------------------------------------------------------------------


def csv_encoding(csv_path):
    """Return the encoding of a DineSafe CSV file: utf-8-sig, else cp1252.

    DineSafe exports mix encodings across files (the recent CSV and the 2001 to
    2022 historical files are UTF-8, dinesafe_hist_2023.csv is Windows-1252), so
    try UTF-8 first and fall back to cp1252. utf-8-sig also accepts a BOM.
    Checks the file in chunks, so it never holds the whole file in memory.
    """
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    with open(csv_path, "rb") as f:
        try:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            return "cp1252"
    return "utf-8-sig"


def open_csv(csv_path, encoding=None):
    """Open a DineSafe CSV file as text for the csv module, in its encoding.
    Pass encoding when it's already known, to skip csv_encoding's full read."""
    return open(csv_path, encoding=encoding or csv_encoding(csv_path), newline="")


def _read_csv_rows(csv_path, column_map, encoding=None):
    """Yield mapped rows from a DineSafe CSV file, one at a time."""
    with open_csv(csv_path, encoding) as f:
        for r in csv.DictReader(f):
            yield map_row(r, column_map)


def _insert_historical_csv(conn, csv_path, cutoff):
    """Stream one historical CSV file into inspections.

    Drops rows on or after cutoff: newer historical archives now extend into
    the recent CSV's date window (for example a 2023 historical file
    alongside a recent feed that also starts in 2023), and inserting both
    would double-count the overlapping inspections.
    """
    inserted = bulk_insert(conn, exclude_on_or_after(_read_csv_rows(csv_path, HISTORICAL_COLUMN_MAP), cutoff))
    print(f"  Loaded {os.path.basename(csv_path)}: {inserted} rows")
    return inserted


class RecentScan(NamedTuple):
    """What the insert pass over the recent CSV needs from the first pass."""
    path: str
    encoding: str
    cutoff: str   # earliest inspection_date
    keys: set     # (old ID, date) pairs that drop_old_id_duplicates drops
    total: int    # row count


def scan_recent(csv_path):
    """First pass over the recent CSV, so the insert pass can stream."""
    print(f"Reading recent data from {csv_path} ...")
    encoding = csv_encoding(csv_path)
    cutoff, keys, total, unparsed = None, set(), 0, 0
    for r in _read_csv_rows(csv_path, RECENT_COLUMN_MAP, encoding):
        total += 1
        date = r["inspection_date"]
        if date is not None and (cutoff is None or date < cutoff):
            cutoff = date
        old_id = r["old_establishment_id"]
        if old_id and old_id != r["establishment_id"]:
            keys.add((old_id, date))
        address = r["establishment_address"]
        unparsed += bool(address) and not _POSTAL_RE.match(address)
    if cutoff is None:
        raise ValueError(f"{csv_path} has no inspection dates")
    # Non-zero means the upstream address format changed; the raw address is kept in street.
    print(f"  Unparsed recent addresses: {unparsed}")
    return RecentScan(csv_path, encoding, cutoff, keys, total)


def _insert_recent(conn, scan):
    """Stream the recent CSV into inspections, without old-ID duplicates."""
    rows = _read_csv_rows(scan.path, RECENT_COLUMN_MAP, scan.encoding)
    inserted = bulk_insert(conn, drop_old_id_duplicates(rows, scan.keys))
    print(f"  Dropped old-ID duplicate rows: {scan.total - inserted}")
    print(f"  Loaded recent CSV: {inserted} rows")
    return inserted


def seed(conn, recent_csv, historical_csvs):
    """Full seed: empty the table, load historical data before the recent
    CSV's date window, then the recent data, so overlapping inspections
    aren't double-counted. historical_csvs is an iterable of paths, read one
    at a time, so the caller can fetch each just before it's needed.
    Doesn't commit. Returns (rows deleted, rows inserted).
    """
    scan = scan_recent(recent_csv)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM inspections")
        deleted = cur.rowcount
    inserted = sum(_insert_historical_csv(conn, path, scan.cutoff) for path in historical_csvs)
    inserted += _insert_recent(conn, scan)
    return deleted, inserted


def refresh(conn, recent_csv):
    """Replace all recent data: delete every row on or after the earliest
    date in the fresh CSV, then insert the CSV. The cutoff tracks the
    upstream data window automatically. Doesn't commit, so the caller's
    single transaction covers the delete, the insert, and the log row.
    Returns (rows deleted, rows inserted).
    """
    scan = scan_recent(recent_csv)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM inspections WHERE inspection_date >= %s", (scan.cutoff,))
        deleted = cur.rowcount
    return deleted, _insert_recent(conn, scan)


# ---------------------------------------------------------------------------
# load_log: which raw-zone files are loaded
# ---------------------------------------------------------------------------


def last_load(conn):
    """Return (recent path of the newest load, historical path of the newest
    seed). Either is None when there's no such load."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT (SELECT recent_path FROM load_log ORDER BY id DESC LIMIT 1), "
            "(SELECT historical_path FROM load_log WHERE kind = 'seed' ORDER BY id DESC LIMIT 1)"
        )
        return cur.fetchone()


def record_load(conn, kind, recent_path, historical_path, deleted, inserted):
    """Insert one load_log row. Doesn't commit."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO load_log (kind, recent_path, historical_path, rows_deleted, rows_inserted) "
            "VALUES (%s, %s, %s, %s, %s)",
            (kind, recent_path, historical_path, deleted, inserted),
        )
