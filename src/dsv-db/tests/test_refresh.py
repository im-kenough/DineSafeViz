import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from refresh import (
    normalize,
    map_row,
    min_inspection_date,
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
    SAMPLE_ROW = {
        "_id": "1",
        "unique_id": "168f86274045194142c0e7c381ccb75d",
        "estId": "001Vo000013QjdPIAS",
        "estName": "HASHTAG INDIA RESTAURANT",
        "address": "1871 O'Connor Dr None M4A 1X1",
        "inspectionStatus": "Pass",
        "inspectionDate": "2024-03-06",
        "typeDesc": "FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED",
        "deficiencyDesc": "None",
        "actionDesc": "Notice to Comply",
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

    def test_historical_only_columns_are_none(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["severity"] is None
        assert result["min_inspections_per_year"] is None

    def test_none_string_becomes_none(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        assert result["inspection_observation"] is None
        assert result["outcome"] is None

    def test_all_inspections_columns_present(self):
        result = map_row(self.SAMPLE_ROW, RECENT_COLUMN_MAP)
        for col in INSPECTIONS_COLUMNS:
            assert col in result, f"Missing column: {col}"
