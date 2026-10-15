import pytest

from fakes import historical_csv, historical_row, recent_csv, recent_row

from loader import (
    normalize,
    normalize_date,
    map_row,
    split_address,
    scan_recent,
    exclude_on_or_after,
    drop_old_id_duplicates,
    _read_csv_rows,
    csv_encoding,
    HISTORICAL_COLUMN_MAP,
    RECENT_COLUMN_MAP,
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


class TestScanRecent:
    # The first pass over the recent CSV, so the second pass can stream.
    def test_cutoff_is_the_earliest_date_skipping_blanks(self, tmp_path):
        p = recent_csv(tmp_path / "r.csv", [recent_row("1", "2024-03-06"), recent_row("2", ""),
                                            recent_row("3", "2023-11-10")])
        cutoff, _, total = scan_recent(str(p))
        assert (cutoff, total) == ("2023-11-10", 3)

    def test_collects_old_id_keys(self, tmp_path):
        p = recent_csv(tmp_path / "r.csv", [
            recent_row("001Vo000013Qna7IAC", "2025-08-18", oldEstId="10820991"),
            recent_row("10820991", "2025-08-18", oldEstId="10820991"),
            recent_row("001Vo000013QjdPIAS", "2026-04-21"),
        ])
        _, keys, _ = scan_recent(str(p))
        assert keys == {("10820991", "2025-08-18")}

    def test_reports_unparsed_addresses(self, tmp_path, capsys):
        # Recent addresses always end in a postal code or "None"; anything
        # else means the upstream format has drifted.
        p = recent_csv(tmp_path / "r.csv", [
            recent_row("1", "2024-01-01", address="65 Front St W Unit-442 M5J 1E6"),
            recent_row("2", "2024-01-01", address="102 Fort York Blvd None None"),
            recent_row("3", "2024-01-01", address="65 Front St W, Toronto ON"),
            recent_row("4", "2024-01-01", address=""),
        ])
        scan_recent(str(p))
        assert "Unparsed recent addresses: 1" in capsys.readouterr().out

    def test_no_dates_is_an_error(self, tmp_path):
        p = recent_csv(tmp_path / "r.csv", [recent_row("1", "")])
        with pytest.raises(ValueError, match="no inspection dates"):
            scan_recent(str(p))


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
        result = map_row(self.SAMPLE_ROW, HISTORICAL_COLUMN_MAP)
        assert result["establishment_id"] == "10500438"

    def test_discards_rec_number(self):
        result = map_row(self.SAMPLE_ROW, HISTORICAL_COLUMN_MAP)
        assert "Rec #" not in result

    def test_maps_historical_only_columns(self):
        result = map_row(self.SAMPLE_ROW, HISTORICAL_COLUMN_MAP)
        assert result["establishment_status"] == "Pass"
        assert result["min_inspections_per_year"] == "2"

    def test_recent_only_columns_are_none(self):
        result = map_row(self.SAMPLE_ROW, HISTORICAL_COLUMN_MAP)
        assert result["infraction_category"] is None
        assert result["outcome_date"] is None
        assert result["unique_id"] is None

    def test_empty_values_become_none(self):
        result = map_row(self.SAMPLE_ROW, HISTORICAL_COLUMN_MAP)
        assert result["infraction_details"] is None
        assert result["severity"] is None
        assert result["action"] is None

    def test_all_inspections_columns_present(self):
        result = map_row(self.SAMPLE_ROW, HISTORICAL_COLUMN_MAP)
        for col in INSPECTIONS_COLUMNS:
            assert col in result, f"Missing column: {col}"


class TestMapRecentRow:
    # New (2026) recent CSV schema: adds oldEstId, phone, observation, severity;
    # removes actionDesc.
    SAMPLE_ROW = {
        "_id": "1",
        "unique_id": "168f86274045194142c0e7c381ccb75d",
        "estId": "001Vo000013QjdPIAS",
        "oldEstId": "10752656",
        "estName": "HASHTAG INDIA RESTAURANT",
        "address": "1871 O'Connor Dr None M4A 1X1",
        "inspectionStatus": "Pass",
        "phone": "4167522786",
        "inspectionDate": "2024-03-06",
        "observation": "One or more minor infractions were observed.",
        "typeDesc": "FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED",
        "deficiencyDesc": "05. MAINTENANCE / SANITATION",
        "severity": "M - Minor",
        "OutcomeDate": "",
        "OutcomeDesc": "None",
        "amountFined": "",
        "latitude": "43.72199",
        "longitude": "-79.30349",
    }

    def test_maps_establishment_id(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["establishment_id"] == "001Vo000013QjdPIAS"

    def test_discards_id(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert "_id" not in result

    def test_keeps_old_establishment_id_for_dedup(self):
        # Not an inspections column: map_row must still carry it so
        # drop_old_id_duplicates can read it before bulk_insert drops it.
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["old_establishment_id"] == "10752656"
        assert "old_establishment_id" not in INSPECTIONS_COLUMNS

    def test_maps_recent_only_columns(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["establishment_status"] == "Pass"
        assert result["unique_id"] == "168f86274045194142c0e7c381ccb75d"

    def test_maps_infraction_and_observation(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["infraction_details"] == "FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED"
        assert result["infraction_category"] == "05. MAINTENANCE / SANITATION"

    def test_maps_severity(self):
        # Severity is now present in the recent feed (was historical-only before).
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["severity"] == "M - Minor"

    def test_action_is_none(self):
        # The recent feed no longer carries an action/enforcement column.
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["action"] is None

    def test_historical_only_columns_are_none(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["min_inspections_per_year"] is None
        assert result["establishment_type"] is None

    def test_none_string_becomes_none(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["outcome"] is None

    def test_all_inspections_columns_present(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        for col in INSPECTIONS_COLUMNS:
            assert col in result, f"Missing column: {col}"


class TestSplitAddress:
    # Recent feed: "{street} {unit} {postal}" with "None" for missing parts.
    def test_recent_no_unit(self):
        assert split_address("1871 O'Connor Dr None M4A 1X1") == ("1871 O'Connor Dr", None, "M4A 1X1")

    def test_recent_with_unit(self):
        assert split_address("65 Front St W Unit-442 M5J 1E6") == ("65 Front St W", "Unit-442", "M5J 1E6")

    def test_recent_no_unit_no_postal(self):
        assert split_address("102 Fort York Blvd None None") == ("102 Fort York Blvd", None, None)

    def test_recent_unit_with_spaces_and_no_postal(self):
        assert split_address("41 Lebovic Ave Unit-A 110 None") == ("41 Lebovic Ave", "Unit-A 110", None)

    def test_recent_unit_containing_commas(self):
        assert split_address("23 Comay Rd Rm-211, 212, 213 M3J 2B5") == ("23 Comay Rd", "Rm-211, 212, 213", "M3J 2B5")

    def test_recent_unit_without_marker_stays_in_street(self):
        assert split_address("80 Western Battery Rd 4 M6K 3S1") == ("80 Western Battery Rd 4", None, "M6K 3S1")

    def test_recent_legacy_comma_address(self):
        assert split_address("4700 KEELE ST, Rm-006 None M3J 1P3") == ("4700 KEELE ST", "Rm-006", "M3J 1P3")

    # Historical CSVs: "{street}, {unit}" or just "{street}", never a postal code.
    def test_historical_with_unit(self):
        assert split_address("266 EDDYSTONE AVE, Unit-0") == ("266 EDDYSTONE AVE", "Unit-0", None)

    def test_historical_unit_without_marker(self):
        assert split_address("301 FRONT ST W, CN TOWER") == ("301 FRONT ST W", "CN TOWER", None)

    def test_historical_comma_wins_over_later_marker(self):
        assert split_address("1235 WILSON AVE, Lower Level-Unit-4") == ("1235 WILSON AVE", "Lower Level-Unit-4", None)

    def test_historical_street_only(self):
        assert split_address("361 OAKWOOD AVE") == ("361 OAKWOOD AVE", None, None)

    def test_none(self):
        assert split_address(None) == (None, None, None)


class TestMapRowSplitsAddress:
    def test_recent_row_keeps_raw_and_splits(self):
        result = map_row({"address": "65 Front St W Unit-442 M5J 1E6"}, RECENT_COLUMN_MAP)
        assert result["establishment_address"] == "65 Front St W Unit-442 M5J 1E6"
        assert (result["street"], result["unit"], result["postal_code"]) == ("65 Front St W", "Unit-442", "M5J 1E6")

    def test_historical_row_splits(self):
        result = map_row({"Establishment Address": "266 EDDYSTONE AVE, Unit-0"}, HISTORICAL_COLUMN_MAP)
        assert (result["street"], result["unit"], result["postal_code"]) == ("266 EDDYSTONE AVE", "Unit-0", None)


class TestReadCsvRows:
    # Historical exports mix encodings: older years are UTF-8, newer files are
    # Windows-1252. The reader must handle both.
    HEADER = (
        "Establishment ID,Establishment Name,Inspection Date\n"
    )

    def test_reads_utf8_file(self, tmp_path):
        p = tmp_path / "utf8.csv"
        p.write_text(self.HEADER + "1,CAFÉ MONTRÉAL,2024-01-01\n", encoding="utf-8")
        rows = list(_read_csv_rows(str(p), HISTORICAL_COLUMN_MAP))
        assert rows[0]["establishment_name"] == "CAFÉ MONTRÉAL"

    def test_reads_windows1252_file(self, tmp_path):
        p = tmp_path / "cp1252.csv"
        p.write_bytes((self.HEADER + "1,CAFÉ MONTRÉAL,2024-01-01\n").encode("cp1252"))
        rows = list(_read_csv_rows(str(p), HISTORICAL_COLUMN_MAP))
        assert rows[0]["establishment_name"] == "CAFÉ MONTRÉAL"


class TestNormalizeDate:
    # dinesafe_hist_2023.csv is the one historical file that uses MM/DD/YYYY
    # instead of the ISO YYYY-MM-DD every other year (and the recent CSV) use.
    def test_iso_date_unchanged(self):
        assert normalize_date("2023-11-10") == "2023-11-10"

    def test_us_slash_date_converted_to_iso(self):
        assert normalize_date("01/03/2023") == "2023-01-03"

    def test_us_slash_date_pads_single_digits(self):
        assert normalize_date("1/3/2023") == "2023-01-03"

    def test_none_unchanged(self):
        assert normalize_date(None) is None


class TestMapRowNormalizesDate:
    def test_historical_mm_dd_yyyy_becomes_iso(self):
        row = {"Inspection Date": "01/03/2023"}
        result = map_row(row, HISTORICAL_COLUMN_MAP)
        assert result["inspection_date"] == "2023-01-03"


class TestDropOldIdDuplicates:
    @staticmethod
    def row(est_id, old_id, date):
        return {"establishment_id": est_id, "old_establishment_id": old_id, "inspection_date": date}

    # keys are the (old ID, date) pairs scan_recent found under a new ID.
    KEYS = {("10820991", "2025-08-18")}

    def test_drops_old_id_row_when_new_id_has_same_inspection(self):
        new = self.row("001Vo000013Qna7IAC", "10820991", "2025-08-18")
        old = self.row("10820991", "10820991", "2025-08-18")
        assert list(drop_old_id_duplicates([old, new], self.KEYS)) == [new]

    def test_keeps_old_id_row_on_a_different_date(self):
        new = self.row("001Vo000013Qna7IAC", "10820991", "2025-08-18")
        old = self.row("10820991", "10820991", "2024-02-01")
        assert list(drop_old_id_duplicates([old, new], self.KEYS)) == [old, new]

    def test_keeps_new_id_row_without_old_id(self):
        new = self.row("001Vo000013QjdPIAS", None, "2026-04-21")
        assert list(drop_old_id_duplicates([new], self.KEYS)) == [new]


class TestExcludeOnOrAfter:
    # The 2023 historical CSV and the recent CSV both cover 2023-11-10
    # onward, so historical rows in that window must be dropped before
    # insert or every inspection in the overlap gets double-counted.
    def test_drops_rows_on_or_after_cutoff(self):
        rows = [
            {"inspection_date": "2023-11-09"},
            {"inspection_date": "2023-11-10"},
            {"inspection_date": "2023-12-29"},
        ]
        result = list(exclude_on_or_after(rows, "2023-11-10"))
        assert result == [{"inspection_date": "2023-11-09"}]

    def test_keeps_none_dates(self):
        rows = [{"inspection_date": None}, {"inspection_date": "2023-11-10"}]
        assert list(exclude_on_or_after(rows, "2023-11-10")) == [{"inspection_date": None}]


class TestCsvEncoding:
    def test_utf8_with_bom(self, tmp_path):
        p = tmp_path / "a.csv"
        p.write_bytes("\ufeffa,b\n".encode("utf-8"))
        assert csv_encoding(str(p)) == "utf-8-sig"

    def test_falls_back_to_cp1252(self, tmp_path):
        p = tmp_path / "a.csv"
        p.write_bytes("caf\xe9\n".encode("cp1252"))
        assert csv_encoding(str(p)) == "cp1252"



from loader import COPY_BATCH, bulk_insert, last_load, record_load, refresh, seed


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.executed.append((" ".join(sql.split()), params))
        self.rowcount = self.conn.delete_rowcount if sql.lstrip().startswith("DELETE") else 0

    def copy_from(self, buf, table, columns):
        self.conn.batches.append(sum(1 for _ in buf))

    def fetchone(self):
        return self.conn.fetch


class FakeConn:
    def __init__(self, delete_rowcount=0, fetch=None):
        self.delete_rowcount = delete_rowcount
        self.fetch = fetch
        self.executed = []
        self.batches = []
        self.commits = 0

    @property
    def copied(self):
        return sum(self.batches)

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def files(tmp_path):
    """The recent CSV and the historical CSVs, in load order."""
    recent = recent_csv(tmp_path / "Dinesafe.csv",
                        [recent_row("1", "2023-05-01"), recent_row("2", "2024-01-02")])
    h22 = historical_csv(tmp_path / "dinesafe_hist_2022.csv", [historical_row("9", "2022-03-01")])
    h23 = historical_csv(tmp_path / "dinesafe_hist_2023.csv",
                         [historical_row("8", "2023-04-30"), historical_row("7", "2023-05-01")])
    return str(recent), [str(h22), str(h23)]


class TestBulkInsert:
    def test_copies_in_batches_and_counts(self):
        conn = FakeConn()
        rows = ({col: None for col in INSPECTIONS_COLUMNS} for _ in range(COPY_BATCH + 1))
        assert bulk_insert(conn, rows) == COPY_BATCH + 1
        assert conn.batches == [COPY_BATCH, 1]

    def test_no_rows_copies_nothing(self):
        conn = FakeConn()
        assert bulk_insert(conn, iter([])) == 0
        assert conn.batches == []


class TestSeedAndRefresh:
    def test_seed_skips_historical_rows_in_the_recent_window(self, tmp_path):
        conn = FakeConn()
        recent, historical = files(tmp_path)
        assert seed(conn, recent, historical) == (0, 4)  # 2 historical before 2023-05-01, 2 recent
        assert conn.copied == 4

    def test_seed_empties_the_table_first(self, tmp_path):
        # A reseed replaces every row, so a new historical folder can't
        # double-count the old one.
        conn = FakeConn(delete_rowcount=7)
        recent, historical = files(tmp_path)
        assert seed(conn, recent, historical) == (7, 4)
        assert conn.executed[0] == ("DELETE FROM inspections", None)

    def test_seed_reads_historical_files_one_at_a_time(self, tmp_path):
        # pipeline.py downloads each file just before seed reads it.
        conn = FakeConn()
        recent, historical = files(tmp_path)
        seen = []

        def lazily():
            for path in historical:
                seen.append(conn.copied)
                yield path

        seed(conn, recent, lazily())
        assert seen == [0, 1]  # the 2023 file was fetched after 2022's rows went in

    def test_refresh_deletes_from_the_cutoff_and_inserts(self, tmp_path):
        conn = FakeConn(delete_rowcount=5)
        recent, _ = files(tmp_path)
        assert refresh(conn, recent) == (5, 2)
        assert ("DELETE FROM inspections WHERE inspection_date >= %s", ("2023-05-01",)) in conn.executed

    def test_recent_old_id_duplicates_are_dropped(self, tmp_path, capsys):
        conn = FakeConn()
        recent = recent_csv(tmp_path / "Dinesafe.csv", [
            recent_row("10820991", "2025-08-18", oldEstId="10820991"),
            recent_row("001Vo000013Qna7IAC", "2025-08-18", oldEstId="10820991"),
        ])
        assert refresh(conn, str(recent)) == (0, 1)
        assert "Dropped old-ID duplicate rows: 1" in capsys.readouterr().out

    def test_neither_commits(self, tmp_path):
        conn = FakeConn()
        recent, historical = files(tmp_path)
        seed(conn, recent, historical)
        refresh(conn, recent)
        assert conn.commits == 0


class TestLoadLog:
    def test_last_load_of_empty_log_is_none(self):
        assert last_load(FakeConn(fetch=(None, None))) == (None, None)

    def test_last_load_returns_newest_load_and_newest_seed(self):
        conn = FakeConn(fetch=("recent/20261012T113012Z/Dinesafe.csv", "historical/20261001T113000Z/"))
        assert last_load(conn) == ("recent/20261012T113012Z/Dinesafe.csv", "historical/20261001T113000Z/")
        sql = conn.executed[0][0]
        assert "ORDER BY id DESC LIMIT 1" in sql
        assert "kind = 'seed'" in sql

    def test_record_load_inserts_one_row(self):
        conn = FakeConn()
        record_load(conn, "seed", "recent/t/Dinesafe.csv", "historical/t/", 0, 10)
        sql, params = conn.executed[0]
        assert sql.startswith("INSERT INTO load_log")
        assert params == ("seed", "recent/t/Dinesafe.csv", "historical/t/", 0, 10)
        assert conn.commits == 0
