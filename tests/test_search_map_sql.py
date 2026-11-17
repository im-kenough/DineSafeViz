"""The app's map query against the real Postgres image, migrated."""
import sys

import pytest

from db_helpers import app_query, replace_inspections
from helpers import ROOT

sys.path.insert(0, str(ROOT / "src" / "dsv-app"))
import app as app_module

# (establishment_id, name, street, status, date, latitude, longitude).
# A1 moved: its newest coordinates win. B1's newest row has no coordinates,
# so its pin uses the older row's, but its status and date are the newest
# row's. N1 never has coordinates, so it gets no pin.
ROWS = [
    ("A1", "Pizza Pizza", "123 Queen St W", "Pass", "2026-10-03", 43.65, -79.38),
    ("A1", "Pizza Pizza", "123 Queen St W", "Conditional Pass", "2025-04-08", 43.60, -79.30),
    ("B1", "Queen Pizza Bar", "9 King St E", "Closed", "2026-01-05", 43.649, -79.37),
    ("B1", "Queen Pizza Bar", "9 King St E", "Pass", "2026-06-01", None, None),
    ("C1", "Sushi Place", "55 Queen St W", "Pass", "2026-09-01", 43.64, -79.39),
    ("N1", "Nowhere Pizza", "1 Lost St", "Pass", "2026-02-02", None, None),
]


@pytest.fixture(scope="module")
def map_db(ready_db):
    replace_inspections(
        ready_db,
        ("establishment_id", "establishment_name", "establishment_address", "street",
         "establishment_status", "inspection_date", "latitude", "longitude"),
        [(eid, n, a, a, s, d, lat, lng) for eid, n, a, s, d, lat, lng in ROWS],
    )
    return ready_db


def pins(name, terms):
    return app_query(name, app_module.search_map_query(terms))


def test_pins_follow_list_order_and_skip_unlocated(map_db):
    listed = [r["establishment_id"] for r in app_query(map_db, app_module.search_query(["pizza"]))]
    pinned = [r["establishment_id"] for r in pins(map_db, ["pizza"])]
    assert listed == ["A1", "B1", "N1"]
    assert pinned == ["A1", "B1"]


def test_pin_uses_newest_located_row(map_db):
    by_id = {r["establishment_id"]: r for r in pins(map_db, ["pizza"])}
    assert (by_id["A1"]["latitude"], by_id["A1"]["longitude"]) == (43.65, -79.38)
    assert (by_id["B1"]["latitude"], by_id["B1"]["longitude"]) == (43.649, -79.37)
    assert by_id["B1"]["establishment_status"] == "Pass"
    assert str(by_id["B1"]["last_inspected"]) == "2026-06-01"


def test_pins_respect_the_limit(map_db, monkeypatch):
    monkeypatch.setattr(app_module, "SEARCH_MAP_LIMIT", 1)
    assert [r["establishment_id"] for r in pins(map_db, ["pizza"])] == ["A1"]


def test_every_word_must_match(map_db):
    assert [r["establishment_id"] for r in pins(map_db, ["pizza", "king"])] == ["B1"]


def test_map_sql_has_no_user_input():
    query, params = app_module.search_map_query(["pizza'; drop"])
    assert "pizza" not in query.as_string(None)
    assert params[-1] == app_module.SEARCH_MAP_LIMIT
