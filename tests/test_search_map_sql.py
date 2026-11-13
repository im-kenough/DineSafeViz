"""The app's map query against the real Postgres image, migrated."""
import sys
from contextlib import closing

import psycopg2
import pytest

from db_helpers import container_ip, migrated_db, psql
from helpers import ROOT

sys.path.insert(0, str(ROOT / "src" / "dsv-app"))
import app as app_module

APP_PW = "app-pw"

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


def _sql_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, float):
        return repr(v)
    return "'" + v + "'"


@pytest.fixture(scope="module")
def map_db():
    env = {"DSV_DB_APP_PASSWORD": APP_PW, "DSV_DB_MIGRATOR_PASSWORD": "migrator-pw"}
    with migrated_db(env) as name:
        values = ", ".join(
            "(" + ", ".join(_sql_value(v) for v in (eid, n, a, a, s, d, lat, lng)) + ")"
            for eid, n, a, s, d, lat, lng in ROWS
        )
        result = psql(name, (
            "INSERT INTO inspections (establishment_id, establishment_name,"
            " establishment_address, street, establishment_status, inspection_date,"
            " latitude, longitude)"
            f" VALUES {values}"
        ))
        assert result.returncode == 0, result.stderr
        yield name


def _run(name, query):
    """Run one (sql, params) pair as dinesafe_app. Returns the result dicts."""
    conn = psycopg2.connect(
        host=container_ip(name), dbname="dinesafe", user="dinesafe_app",
        password=APP_PW, connect_timeout=5,
    )
    with closing(conn), conn.cursor() as cur:
        cur.execute(*query)
        columns = [c.name for c in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def pins(name, terms):
    return _run(name, app_module.search_map_query(terms))


def test_pins_follow_list_order_and_skip_unlocated(map_db):
    listed = [r["establishment_id"] for r in _run(map_db, app_module.search_query(["pizza"]))]
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
