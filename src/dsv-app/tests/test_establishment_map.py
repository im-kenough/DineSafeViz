"""The restaurant page's one-pin map."""
import json
import re
from datetime import date
from unittest.mock import patch

import app as app_module
from db_fakes import rows_conn
from test_establishment import EST_ID, _row


def _located(day, lat=43.65, lng=-79.38, **kwargs):
    return {**_row(day, **kwargs), "latitude": lat, "longitude": lng}


def _get(client, rows):
    with patch("app.psycopg2.connect", return_value=rows_conn(rows)):
        resp = client.get(f"/establishment/{EST_ID}")
    assert resp.status_code == 200
    return resp.data.decode()


def test_establishment_pin_uses_newest_located_row():
    rows = [
        _located(date(2024, 3, 1), lat=43.60, lng=-79.30),
        _located(date(2026, 10, 3), lat=None, lng=None),
        _located(date(2025, 4, 8), lat=43.65, lng=-79.38),
    ]
    with app_module.app.test_request_context():
        pin = app_module.establishment_pin(rows)
    assert (pin["lat"], pin["lng"]) == (43.65, -79.38)
    assert pin["url"] == f"/establishment/{EST_ID}"


def test_establishment_pin_none_without_coordinates():
    with app_module.app.test_request_context():
        assert app_module.establishment_pin([_located(date(2026, 10, 3), lat=None, lng=None)]) is None


def test_page_has_single_map_between_heading_and_history(client):
    html = _get(client, [_located(date(2026, 10, 3))])
    assert 'class="map map-single"' in html
    assert re.search(r'<div id="map"[^>]* data-single hidden></div>', html)
    assert 'aria-label="Map of Pizza Pizza"' in html
    pins = json.loads(re.search(r'id="map-data">(.*?)</script>', html, re.S).group(1))
    assert len(pins) == 1
    assert "/static/vendor/leaflet/leaflet.js" in html
    assert html.index("</h2>") < html.index('id="map"') < html.index("Saturday, October 3, 2026")


def test_page_without_coordinates_has_no_map(client):
    html = _get(client, [_located(date(2026, 10, 3), lat=None, lng=None)])
    assert 'id="map"' not in html
    assert "leaflet" not in html
    assert "Pizza Pizza" in html


def test_nameless_restaurant_label(client):
    html = _get(client, [_located(date(2026, 10, 3), name=None)])
    assert 'aria-label="Map of this restaurant"' in html


def test_select_fetches_coordinates():
    assert "latitude, longitude" in app_module._INSPECTION_SELECT
