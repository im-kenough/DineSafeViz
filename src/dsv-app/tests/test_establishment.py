from datetime import date
from unittest.mock import patch

import pytest

import app as app_module
from db_fakes import rows_conn

EST_ID = "001Vo000013QjdPIAS"


def _row(day, status="Pass", details=None, severity=None, name="Pizza Pizza",
         street="123 Queen St W", unit=None):
    """One row as returned by _fetch_establishment's RealDictCursor query."""
    return {
        "inspection_date": day,
        "establishment_status": status,
        "action": None,
        "infraction_details": details,
        "establishment_name": name,
        "establishment_address": f"{street} M5V 2A1",
        "establishment_type": None,
        "street": street,
        "unit": unit,
        "postal_code": None,
        "outcome": None,
        "outcome_date": None,
        "amount_fined": None,
        "establishment_id": EST_ID,
        "severity": severity,
        "infraction_category": None,
    }


def _get(client, url, rows=()):
    with patch("app.psycopg2.connect", return_value=rows_conn(list(rows))) as connect:
        resp = client.get(url)
    return resp, connect


def test_build_history_groups_by_date_newest_first():
    rows = [
        _row(date(2024, 3, 1), details="Minor thing", severity="M - Minor"),
        _row(date(2026, 10, 3)),
        _row(date(2024, 3, 1), details="Crucial thing", severity="C - Crucial"),
    ]
    days = app_module.build_history(rows)
    assert [d for d, _ in days] == [date(2026, 10, 3), date(2024, 3, 1)]
    assert [len(ests) for _, ests in days] == [1, 1]
    assert [i["infraction_details"] for i in days[1][1][0]["infractions"]] == ["Crucial thing", "Minor thing"]


def test_establishment_page_lists_every_inspection_newest_first(client):
    rows = [
        _row(date(2019, 3, 4), status="Conditional Pass", details="Pests", severity="S - Significant"),
        _row(date(2026, 10, 3), name="Pizza Pizza Queen", unit="Unit 2"),
    ]
    resp, _ = _get(client, f"/establishment/{EST_ID}", rows)
    html = resp.data.decode()
    assert resp.status_code == 200
    # Heading and title come from the newest row.
    assert "<title>DineSafeViz - Pizza Pizza Queen</title>" in html
    assert "123 Queen St W Unit 2, Toronto, ON" in html
    assert "2 inspections, March 4, 2019 to October 3, 2026" in html
    assert html.index("Saturday, October 3, 2026") < html.index("Monday, March 4, 2019")
    assert "status-conditional" in html
    assert "Pests" in html


def test_establishment_page_with_one_inspection(client):
    resp, _ = _get(client, f"/establishment/{EST_ID}", [_row(date(2026, 10, 3))])
    assert "1 inspection, October 3, 2026" in resp.data.decode()


def test_unknown_id_is_404(client):
    resp, connect = _get(client, "/establishment/12345", [])
    assert resp.status_code == 404
    connect.assert_called_once()


@pytest.mark.parametrize("bad_id", ["abc-def", "a" * 33, "12%2034", "abc.def"])
def test_malformed_id_is_404_without_db(client, bad_id):
    resp, connect = _get(client, f"/establishment/{bad_id}")
    assert resp.status_code == 404
    connect.assert_not_called()


def test_inspection_cards_link_to_establishment_page(client):
    row = _row(date(2024, 2, 14))
    resp, _ = _get(client, "/inspections/month?year=2024&m=2", [row])
    assert f'<a class="est-link" href="/establishment/{EST_ID}">Pizza Pizza</a>' in resp.data.decode()


def test_card_without_establishment_id_shows_plain_name(client):
    # The loader stores an empty Establishment ID as NULL, and url_for can't build
    # a link without one, so the name renders unlinked instead of a 500.
    row = _row(date(2024, 2, 14)) | {"establishment_id": None}
    resp, _ = _get(client, "/inspections/month?year=2024&m=2", [row])
    html = resp.data.decode()
    assert resp.status_code == 200
    assert "<strong>Pizza Pizza</strong>" in html
    assert "est-link" not in html
