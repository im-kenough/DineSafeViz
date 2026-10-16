"""DineSafe source CSV format: file names, column maps, and encoding."""

import codecs
import os

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
# import). "oldEstId" is read only by loader.scan_recent and isn't stored:
# loader.bulk_insert writes only INSPECTIONS_COLUMNS. The recent feed no
# longer carries an "actionDesc" column, so `action` stays NULL for recent rows.
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


class EncodingDetector:
    """Incremental csv_encoding: feed() the bytes in chunks, then call result().

    Lets a caller detect the encoding in the same pass as other work over the
    bytes, such as a checksum. utf8 turns False at the first invalid byte.
    """

    def __init__(self):
        self._decoder = codecs.getincrementaldecoder("utf-8-sig")()
        self.utf8 = True

    def feed(self, chunk):
        if self.utf8:
            try:
                self._decoder.decode(chunk)
            except UnicodeDecodeError:
                self.utf8 = False

    def result(self):
        """Return utf-8-sig or cp1252. Call once, after the last chunk."""
        if self.utf8:
            try:
                self._decoder.decode(b"", final=True)
            except UnicodeDecodeError:
                self.utf8 = False
        return "utf-8-sig" if self.utf8 else "cp1252"


def csv_encoding(source):
    """Return the encoding of a DineSafe CSV file or binary stream: utf-8-sig,
    else cp1252.

    DineSafe exports mix encodings across files (the recent CSV and the 2001 to
    2022 historical files are UTF-8, dinesafe_hist_2023.csv is Windows-1252), so
    try UTF-8 first and fall back to cp1252. utf-8-sig also accepts a BOM.
    Checks the input in chunks, so it never holds the whole file in memory.
    A stream is consumed (to EOF, or to the first non-UTF-8 byte) and not
    rewound; the caller must reopen or seek it before reading it again.
    """
    if isinstance(source, (str, os.PathLike)):
        with open(source, "rb") as f:
            return csv_encoding(f)
    detector = EncodingDetector()
    for chunk in iter(lambda: source.read(1 << 20), b""):
        detector.feed(chunk)
        if not detector.utf8:
            break  # already decided
    return detector.result()


def open_csv(csv_path, encoding=None):
    """Open a DineSafe CSV file as text for the csv module, in its encoding.
    Pass encoding when it's already known, to skip csv_encoding's full read."""
    return open(csv_path, encoding=encoding or csv_encoding(csv_path), newline="")
