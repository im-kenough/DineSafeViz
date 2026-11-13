"""The results-page map: pin data, container, scripts, and the over-limit note."""
import json
import re
from datetime import date
from pathlib import Path
from unittest.mock import patch

import app as app_module
from db_fakes import search_conn

_STYLE_CSS = Path(__file__).resolve().parent.parent / "static" / "style.css"


def _pin_row(n=1, name="Starbucks", status="Pass", unit=None, lat=43.65, lng=-79.38):
    """One row as returned by the map query's RealDictCursor."""
    return {
        "establishment_id": f"001Vo0000000000{n:03d}",
        "establishment_name": name,
        "street": "123 Queen St W",
        "unit": unit,
        "establishment_status": status,
        "last_inspected": date(2026, 10, 3),
        "latitude": lat,
        "longitude": lng,
    }


def _page_row(n=1):
    """One row as returned by the page query (see test_search._result)."""
    return {
        "establishment_id": f"001Vo0000000000{n:03d}",
        "establishment_name": "Starbucks",
        "street": "123 Queen St W",
        "unit": None,
        "establishment_status": "Pass",
        "last_inspected": date(2026, 10, 3),
        "inspection_count": 3,
        "first_inspected": date(2020, 1, 1),
        "establishment_type": None,
    }


def _get(client, pins, total=None, rows=None, query_string=None):
    rows = [_page_row()] if rows is None else rows
    conn = search_conn(rows, total=len(pins) if total is None else total, pins=pins)
    with patch("app.psycopg2.connect", return_value=conn):
        resp = client.get("/search", query_string=query_string or {"q": "starbucks"})
    assert resp.status_code == 200
    return resp.data.decode(), conn.cursor.return_value


def _map_data(html):
    m = re.search(r'<script type="application/json" id="map-data">(.*?)</script>', html, re.S)
    assert m, "no map-data block"
    return json.loads(m.group(1))


def test_map_pin_shape():
    with app_module.app.test_request_context():
        pin = app_module.map_pin(_pin_row(unit="Unit 2", status="Conditional Pass"))
    assert pin == {
        "lat": 43.65, "lng": -79.38,
        "name": "Starbucks", "addr": "123 Queen St W Unit 2",
        "status": "Conditional Pass", "cls": "status-conditional",
        "last": "October 3, 2026",
        "url": "/establishment/001Vo0000000000001",
    }


def test_map_pin_without_name_uses_dash():
    with app_module.app.test_request_context():
        assert app_module.map_pin(_pin_row(name=None))["name"] == "—"


def test_results_page_has_map_and_pins(client):
    html, _ = _get(client, [_pin_row(1), _pin_row(2, status="Closed")])
    assert 'class="map map-results"' in html
    assert 'aria-label="Map of 2 restaurants. The list below has the same results."' in html
    assert [p["cls"] for p in _map_data(html)] == ["status-pass", "status-closed"]
    assert "/static/vendor/leaflet/leaflet.js" in html
    assert "/static/vendor/leaflet/leaflet.css" in html
    assert "/static/map.js" in html
    # The map comes before the list.
    assert html.index('id="map"') < html.index('class="results"')


def test_map_container_starts_hidden(client):
    html, _ = _get(client, [_pin_row()])
    assert re.search(r'<div id="map"[^>]* hidden></div>', html)


def test_no_map_without_matches(client):
    html, _ = _get(client, [], total=0, rows=[])
    assert 'id="map"' not in html
    assert "leaflet" not in html


def test_no_map_without_query(client):
    with patch("app.psycopg2.connect") as connect:
        html = client.get("/search").data.decode()
    connect.assert_not_called()
    assert 'id="map"' not in html
    assert "leaflet" not in html


def test_no_map_when_no_match_has_coordinates(client):
    html, _ = _get(client, [], total=1)
    assert 'id="map"' not in html


def test_map_data_escapes_script_close(client):
    name = "</script><script>alert(1)</script> & 'Joe's'"
    html, _ = _get(client, [_pin_row(name=name)])
    assert "<script>alert(1)" not in html
    assert _map_data(html)[0]["name"] == name


def test_over_limit_note_uses_commas(client):
    pins = [_pin_row(n) for n in range(1, 4)]
    html, _ = _get(client, pins, total=2732)
    assert "Showing 3 of 2,732 on the map. Add a word to narrow it down." in html


def test_no_note_when_every_match_is_on_the_map(client):
    html, _ = _get(client, [_pin_row(1), _pin_row(2)], total=2)
    assert "on the map." not in html


def test_page_past_end_still_has_map(client):
    html, cur = _get(client, [_pin_row()], total=1, rows=[],
                     query_string={"q": "starbucks", "page": "99"})
    assert 'id="map"' in html
    # count and map queries only; the page query is skipped.
    assert cur.execute.call_count == 2


def test_map_query_params(client):
    _, cur = _get(client, [_pin_row()])
    _, (pins_sql, pin_params), _ = (c.args for c in cur.execute.call_args_list)
    assert "starbucks" not in pins_sql.as_string(None)
    assert pin_params == ["%starbucks%", "%starbucks%", "starbucks%", app_module.SEARCH_MAP_LIMIT]
    assert app_module.SEARCH_MAP_LIMIT == 1000


def _css_rule(selector):
    """The bodies of every style.css rule whose selector list includes selector."""
    css = re.sub(r"/\*.*?\*/", "", _STYLE_CSS.read_text(), flags=re.S)
    return " ".join(
        body for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", css)
        if selector in (" ".join(s.split()) for s in selectors.split(","))
    )


# leaflet.css loads after style.css, so these selectors need the extra
# .leaflet-container class to outrank Leaflet's own 26-30px controls.
def test_map_zoom_buttons_are_tap_sized():
    body = _css_rule(".map.leaflet-container .leaflet-control-zoom a")
    for decl in ("width: 44px", "height: 44px", "line-height: 44px"):
        assert decl in body


def test_map_popup_close_is_tap_sized_and_clear_of_the_card():
    body = _css_rule(".map.leaflet-container a.leaflet-popup-close-button")
    for decl in ("width: 44px", "height: 44px", "line-height: 44px"):
        assert decl in body
    # The card sits left of the close button, not under it.
    assert "padding-right: 44px" in _css_rule(".map .leaflet-popup-content-wrapper")
