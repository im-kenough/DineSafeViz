import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from refresh import (
    normalize,
    normalize_date,
    map_row,
    split_address,
    count_unparsed_addresses,
    min_inspection_date,
    recent_source,
    historical_source,
    exclude_on_or_after,
    _read_csv_rows,
    RECENT_CSV_URL,
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


class TestMinInspectionDate:
    def test_returns_earliest_date(self):
        rows = [
            {"inspection_date": "2024-03-06"},
            {"inspection_date": "2023-11-10"},
            {"inspection_date": "2024-01-15"},
        ]
        assert min_inspection_date(rows) == "2023-11-10"

    def test_skips_none_dates(self):
        rows = [
            {"inspection_date": None},
            {"inspection_date": "2024-03-06"},
            {"inspection_date": "2023-11-10"},
        ]
        assert min_inspection_date(rows) == "2023-11-10"


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
        assert result["inspection_observation"] is None
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

    def test_maps_recent_only_columns(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["establishment_status"] == "Pass"
        assert result["unique_id"] == "168f86274045194142c0e7c381ccb75d"

    def test_maps_infraction_and_observation(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["infraction_details"] == "FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED"
        assert result["inspection_observation"] == "05. MAINTENANCE / SANITATION"

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


class TestCountUnparsedAddresses:
    # Recent addresses always end in a postal code or "None"; anything else
    # means the upstream format has drifted.
    def test_counts_recent_addresses_without_postal_token(self):
        rows = [
            {"establishment_address": "65 Front St W Unit-442 M5J 1E6"},
            {"establishment_address": "102 Fort York Blvd None None"},
            {"establishment_address": "65 Front St W, Toronto ON"},
            {"establishment_address": None},
        ]
        assert count_unparsed_addresses(rows) == 1


class TestReadCsvRows:
    # Historical exports mix encodings: older years are UTF-8, newer files are
    # Windows-1252. The reader must handle both.
    HEADER = (
        "Establishment ID,Establishment Name,Inspection Date\n"
    )

    def test_reads_utf8_file(self, tmp_path):
        p = tmp_path / "utf8.csv"
        p.write_text(self.HEADER + "1,CAFÉ MONTRÉAL,2024-01-01\n", encoding="utf-8")
        rows = _read_csv_rows(str(p), HISTORICAL_COLUMN_MAP)
        assert rows[0]["establishment_name"] == "CAFÉ MONTRÉAL"

    def test_reads_windows1252_file(self, tmp_path):
        p = tmp_path / "cp1252.csv"
        p.write_bytes((self.HEADER + "1,CAFÉ MONTRÉAL,2024-01-01\n").encode("cp1252"))
        rows = _read_csv_rows(str(p), HISTORICAL_COLUMN_MAP)
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
        result = exclude_on_or_after(rows, "2023-11-10")
        assert result == [{"inspection_date": "2023-11-09"}]

    def test_keeps_none_dates(self):
        rows = [{"inspection_date": None}, {"inspection_date": "2023-11-10"}]
        assert exclude_on_or_after(rows, "2023-11-10") == [{"inspection_date": None}]


class TestDataSourceSelection:
    def test_recent_source_defaults_to_live_url(self):
        assert recent_source("") == RECENT_CSV_URL

    def test_recent_source_uses_local_file_when_set(self):
        assert recent_source("/data") == os.path.join("/data", "Dinesafe.csv")

    def test_historical_source_none_when_unset(self):
        assert historical_source("") is None

    def test_historical_source_uses_local_dir_when_set(self):
        assert historical_source("/data") == os.path.join("/data", "dinesafe-historical")
