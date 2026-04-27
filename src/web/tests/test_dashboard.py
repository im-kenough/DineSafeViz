import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module


def test_dashboard_returns_200():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_dashboard_contains_iframe():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    resp = client.get("/dashboard")
    assert b"<iframe" in resp.data
    assert b"/grafana/d/dinesafe" in resp.data
    assert b"kiosk" in resp.data


def test_dashboard_has_home_link():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    resp = client.get("/dashboard")
    assert b'href="/"' in resp.data
