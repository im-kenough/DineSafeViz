import json
import re
from pathlib import Path


def test_dashboard_returns_200(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_dashboard_contains_iframe(client):
    resp = client.get("/dashboard")
    assert b"<iframe" in resp.data
    assert b"/analytics/d/dinesafe" in resp.data
    assert b"kiosk" in resp.data


def test_dashboard_has_home_link(client):
    resp = client.get("/dashboard")
    assert b'href="/"' in resp.data
    assert b'href="/info"' in resp.data


# The Grafana dashboard can't read CSS variables, so its status colours are
# hard-coded copies of the --dinesafe-* tokens in style.css. Keep them in sync.
_APP_DIR = Path(__file__).resolve().parent.parent
_STYLE_CSS = _APP_DIR / "static" / "style.css"
_DASHBOARD_JSON = _APP_DIR.parent / "dsv-analytics" / "provisioning" / "dashboards" / "dinesafe.json"
_STATUS_TOKENS = {"Pass": "green", "Conditional Pass": "yellow", "Closed": "red"}


def _css_status_colours():
    tokens = dict(re.findall(r"--dinesafe-(\w+):\s*(#[0-9A-Fa-f]{6})", _STYLE_CSS.read_text()))
    return {status: tokens[name].upper() for status, name in _STATUS_TOKENS.items()}


def _panel_status(title):
    # Longest prefix first so "Conditional Pass ..." isn't matched as "Pass".
    for status in sorted(_STATUS_TOKENS, key=len, reverse=True):
        if title.startswith(status):
            return status
    return None


def test_dashboard_status_colours_match_css():
    expected = _css_status_colours()
    panels = json.loads(_DASHBOARD_JSON.read_text())["panels"]
    checked = 0
    for panel in panels:
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        status = _panel_status(panel.get("title", ""))
        if status and panel["type"] != "row":
            colours = []
            if defaults.get("color", {}).get("mode") == "fixed":
                colours.append(defaults["color"]["fixedColor"])
            if panel["type"] == "stat" and "thresholds" in defaults:
                colours.append(defaults["thresholds"]["steps"][0]["color"])
            assert colours, f"panel {panel['title']!r} has no status colour"
            for colour in colours:
                assert colour.upper() == expected[status], f"panel {panel['title']!r}"
                checked += 1
        for override in panel.get("fieldConfig", {}).get("overrides", []):
            status = override["matcher"].get("options")
            if status in expected:
                for prop in override["properties"]:
                    if prop["id"] == "color":
                        assert prop["value"]["fixedColor"].upper() == expected[status], \
                            f"panel {panel['title']!r} override {status!r}"
                        checked += 1
    # Guards against the walk silently matching nothing after a dashboard rework.
    assert checked >= 20
