"""The inspection status on inspection and search result cards sits in a
bordered .status-badge, coloured by the card's status-* class (issue #355)."""
import re
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from db_fakes import search_conn

_STYLE_CSS = Path(__file__).resolve().parent.parent / "static" / "style.css"
EST_ID = "001Vo000013QjdPIAS"


def _inspection(status="Pass"):
    """One inspection row with no infractions, as the card queries return it."""
    return {
        "inspection_date": date(2024, 2, 14),
        "establishment_status": status,
        "action": None,
        "infraction_details": None,
        "establishment_name": "Pizza Pizza",
        "establishment_address": "123 Queen St W",
        "establishment_type": None,
        "street": "123 Queen St W",
        "unit": None,
        "postal_code": None,
        "outcome": None,
        "outcome_date": None,
        "amount_fined": None,
        "establishment_id": EST_ID,
        "severity": None,
        "infraction_category": None,
    }


def _search_result(status="Conditional Pass"):
    return {
        "establishment_id": EST_ID,
        "establishment_name": "Pizza Pizza",
        "street": "123 Queen St W",
        "unit": None,
        "establishment_status": status,
        "last_inspected": date(2026, 10, 3),
        "inspection_count": 14,
        "first_inspected": date(2019, 3, 4),
        "establishment_type": None,
    }


def _get(client, url, rows):
    with patch("app.psycopg2.connect", return_value=search_conn(rows)):
        resp = client.get(url)
    assert resp.status_code == 200
    return resp.data.decode()


def _css_rule(selector):
    """Body of the first style.css rule whose selector list includes selector."""
    css = re.sub(r"/\*.*?\*/", "", _STYLE_CSS.read_text(), flags=re.S)
    for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        if selector in (" ".join(s.split()) for s in selectors.split(",")):
            return body
    return None


@pytest.mark.parametrize("url", [
    "/inspections/month?year=2024&m=2",
    f"/establishment/{EST_ID}",
])
def test_inspection_card_status_in_badge(client, url):
    html = _get(client, url, [_inspection("Conditional Pass")])
    assert ('<span class="label">Inspection Status</span> '
            '<strong class="status-badge">CONDITIONAL PASS</strong>') in html
    assert 'class="est-card status-conditional"' in html


@pytest.mark.parametrize("status", ["Pass", "Conditional Pass", "Closed"])
def test_search_result_status_in_badge(client, status):
    html = _get(client, "/search?q=pizza", [_search_result(status)])
    assert f'<strong class="status-badge">{status.upper()}</strong>' in html


def test_search_result_card_keeps_status_class(client):
    html = _get(client, "/search?q=pizza", [_search_result("Conditional Pass")])
    assert 'class="result-card status-conditional"' in html


def test_badge_css_has_border_and_radius():
    rule = _css_rule(".status-badge")
    assert rule is not None
    assert re.search(r"(^|;|\s)border:\s*[^;]*var\(--border\)", rule)
    assert "border-radius:" in rule
    assert "color: var(--text)" in rule


@pytest.mark.parametrize("status_class, token", [
    ("status-closed", "red"),
    ("status-conditional", "yellow"),
    ("status-pass", "green"),
])
def test_badge_border_colour_follows_card_status(status_class, token):
    rule = _css_rule(f".{status_class} .status-badge")
    assert rule is not None
    assert f"border-color: var(--dinesafe-{token})" in rule


def test_result_card_badge_hugs_its_text():
    rule = _css_rule(".result-latest .status-badge")
    assert rule is not None
    assert "align-self:" in rule


# Unknown statuses get no status-* class, so the badge keeps the var(--border) fallback.
def test_unknown_status_inspection_card_renders_in_badge(client):
    html = _get(client, "/inspections/month?year=2024&m=2", [_inspection("Out of Business")])
    assert '<strong class="status-badge">OUT OF BUSINESS</strong>' in html
    assert 'class="est-card "' in html


def test_unknown_status_search_result_renders_in_badge(client):
    html = _get(client, "/search?q=pizza", [_search_result("Out of Business")])
    assert '<strong class="status-badge">OUT OF BUSINESS</strong>' in html
    assert 'class="result-card "' in html


def test_null_status_renders_dash_in_badge(client):
    html = _get(client, "/inspections/month?year=2024&m=2", [_inspection(None)])
    assert '<strong class="status-badge">—</strong>' in html
