"""The inspection status on inspection and search result cards sits in a
bordered .status-badge, coloured by the card's status-* class (issue #355)."""
import re
from unittest.mock import patch

import pytest

from db_fakes import EST_ID, inspection_row, rows_conn, search_conn, search_row
from style_css import css_rule



def _get(client, url, rows):
    conn = search_conn(rows) if url.startswith("/search") else rows_conn(rows)
    with patch("app.psycopg2.connect", return_value=conn):
        resp = client.get(url)
    assert resp.status_code == 200
    return resp.data.decode()


@pytest.mark.parametrize("url", [
    "/inspections/month?year=2024&m=2",
    f"/establishment/{EST_ID}",
])
def test_inspection_card_status_in_badge(client, url):
    html = _get(client, url, [inspection_row(status="Conditional Pass")])
    assert ('<span class="label">Inspection Status</span> '
            '<strong class="status-badge">CONDITIONAL PASS</strong>') in html
    assert 'class="est-card status-conditional"' in html


@pytest.mark.parametrize("status", ["Pass", "Conditional Pass", "Closed"])
def test_search_result_status_in_badge(client, status):
    html = _get(client, "/search?q=pizza", [search_row(status=status)])
    assert f'<strong class="status-badge">{status.upper()}</strong>' in html


def test_search_result_card_keeps_status_class(client):
    html = _get(client, "/search?q=pizza", [search_row(status="Conditional Pass")])
    assert 'class="result-card status-conditional"' in html


def test_badge_css_has_border_and_radius():
    rule = css_rule(".status-badge")
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
    rule = css_rule(f".{status_class} .status-badge")
    assert rule is not None
    assert f"border-color: var(--dinesafe-{token})" in rule


def test_result_card_badge_hugs_its_text():
    rule = css_rule(".result-latest .status-badge")
    assert rule is not None
    assert "align-self:" in rule


# Unknown statuses get no status-* class, so the badge keeps the var(--border) fallback.
def test_unknown_status_inspection_card_renders_in_badge(client):
    html = _get(client, "/inspections/month?year=2024&m=2", [inspection_row(status="Out of Business")])
    assert '<strong class="status-badge">OUT OF BUSINESS</strong>' in html
    assert 'class="est-card "' in html


def test_unknown_status_search_result_renders_in_badge(client):
    html = _get(client, "/search?q=pizza", [search_row(status="Out of Business")])
    assert '<strong class="status-badge">OUT OF BUSINESS</strong>' in html
    assert 'class="result-card "' in html


def test_null_status_renders_dash_in_badge(client):
    html = _get(client, "/inspections/month?year=2024&m=2", [inspection_row(status=None)])
    assert '<strong class="status-badge">—</strong>' in html
