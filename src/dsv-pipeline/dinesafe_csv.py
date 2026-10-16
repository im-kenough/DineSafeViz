"""DineSafe source CSV format: file names, column maps, and encoding."""

import codecs

RECENT_NAME = "Dinesafe.csv"

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
