"""The app's search SQL against the real Postgres image, migrated."""
import sys
from contextlib import closing
from datetime import date, timedelta

import psycopg2
import pytest

from db_helpers import container_ip, migrated_db, psql
from helpers import ROOT

sys.path.insert(0, str(ROOT / "src" / "dsv-app"))
import app as app_module

APP_PW = "app-pw"

# (establishment_id, name, type, address/street, unit, status, date). A1 has
# two rows on 2026-10-03 (two infractions, one inspection). H1 is the same
# place under its pre-2023 numeric ID.
ROWS = [
    ("A1", "Pizza Pizza", None, "123 Queen St W", None, "Pass", "2026-10-03"),
    ("A1", "Pizza Pizza", None, "123 Queen St W", None, "Pass", "2026-10-03"),
    ("A1", "Pizza Pizza", None, "123 Queen St W", None, "Conditional Pass", "2025-04-08"),
    ("1001", "Pizza Pizza", "Restaurant", "123 Queen St W", None, "Pass", "2019-03-04"),
    ("B1", "Queen Pizza Bar", "Restaurant", "9 King St E", "Unit 2", "Closed", "2026-01-05"),
    ("C1", "Sushi Place", "Restaurant", "55 Queen St W", None, "Pass", "2026-09-01"),
    ("D1", "100% Burgers", "Restaurant", "1 Bay St", None, "Pass", "2026-02-02"),
    ("E1", "1000 Burgers", "Restaurant", "2 Bay St", None, "Pass", "2026-02-03"),
    # A nameless latest row must not outrank a real prefix match.
    ("Q1", "Quux Cafe", "Restaurant", "3 Bay St", None, "Pass", "2025-01-01"),
    ("Q2", None, "Restaurant", "1 Quux St", None, "Pass", "2026-01-01"),
    # One establishment that matches on the address only, newer than all of Z.
    ("Y1", "Big Zorbo", "Restaurant", "4 Bay St", None, "Pass", "2026-09-01"),
]

# More prefix matches than the page holds (SEARCH_LIMIT + 1 of them survive).
# Z01 is the most recently inspected, Z55 the least. Each has an older
# inspection too, so the totals come from rows outside the page's latest row.
ZORBO = 55
for _n in range(1, ZORBO + 1):
    _last = str(date(2026, 8, 1) - timedelta(days=_n))
    ROWS += [
        (f"Z{_n:02d}", f"Zorbo {_n}", "Restaurant", "5 Bay St", None, "Pass", _last),
        (f"Z{_n:02d}", f"Zorbo {_n}", "Restaurant", "5 Bay St", None, "Pass", "2020-01-01"),
    ]


@pytest.fixture(scope="module")
def search_db():
    env = {"DSV_DB_APP_PASSWORD": APP_PW, "DSV_DB_MIGRATOR_PASSWORD": "migrator-pw"}
    with migrated_db(env) as name:
        values = ", ".join(
            "(" + ", ".join("NULL" if v is None else "'" + v + "'" for v in (eid, n, t, a, a, u, s, d)) + ")"
            for eid, n, t, a, u, s, d in ROWS
        )
        result = psql(name, (
            "INSERT INTO inspections (establishment_id, establishment_name, establishment_type,"
            " establishment_address, street, unit, establishment_status, inspection_date)"
            f" VALUES {values}"
        ))
        assert result.returncode == 0, result.stderr
        yield name


def search(name, terms):
    """Run the app's search query as dinesafe_app. Returns the result dicts."""
    conn = psycopg2.connect(
        host=container_ip(name), dbname="dinesafe", user="dinesafe_app",
        password=APP_PW, connect_timeout=5,
    )
    with closing(conn), conn.cursor() as cur:
        cur.execute(*app_module.search_query(terms))
        columns = [c.name for c in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def test_pizza_ranks_prefix_then_recent(search_db):
    results = search(search_db, ["pizza"])
    assert [r["establishment_id"] for r in results] == ["A1", "1001", "B1"]
    a1 = results[0]
    assert a1["establishment_status"] == "Pass"
    assert str(a1["last_inspected"]) == "2026-10-03"
    assert str(a1["first_inspected"]) == "2025-04-08"
    assert a1["inspection_count"] == 2
    assert a1["establishment_type"] is None
    assert results[1]["establishment_type"] == "Restaurant"
    assert results[2]["unit"] == "Unit 2"


def test_every_word_must_match_name_or_address(search_db):
    assert [r["establishment_id"] for r in search(search_db, ["sushi", "queen"])] == ["C1"]
    assert [r["establishment_id"] for r in search(search_db, ["pizza", "king"])] == ["B1"]


def test_percent_matches_literally(search_db):
    assert [r["establishment_id"] for r in search(search_db, ["100%"])] == ["D1"]


def test_result_columns_match_the_template(search_db):
    assert list(search(search_db, ["sushi"])[0]) == [
        "establishment_id", "establishment_name", "street", "unit",
        "establishment_status", "last_inspected", "inspection_count",
        "first_inspected", "establishment_type",
    ]


def test_nameless_row_does_not_outrank_prefix_match(search_db):
    assert [r["establishment_id"] for r in search(search_db, ["quux"])] == ["Q1", "Q2"]


def test_limit_keeps_the_best_ranked_page(search_db):
    results = search(search_db, ["zorbo"])
    # Prefix matches beat the newer Y1, then newest first; the limit trims the rest.
    assert len(results) == app_module.SEARCH_LIMIT + 1
    assert [r["establishment_id"] for r in results] == [
        f"Z{n:02d}" for n in range(1, app_module.SEARCH_LIMIT + 2)
    ]
    for r in results:
        assert r["inspection_count"] == 2
        assert str(r["first_inspected"]) == "2020-01-01"
        assert r["establishment_type"] == "Restaurant"
