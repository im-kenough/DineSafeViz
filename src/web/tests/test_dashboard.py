def test_dashboard_returns_200(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_dashboard_contains_iframe(client):
    resp = client.get("/dashboard")
    assert b"<iframe" in resp.data
    assert b"/grafana/d/dinesafe" in resp.data
    assert b"kiosk" in resp.data


def test_dashboard_has_home_link(client):
    resp = client.get("/dashboard")
    assert b'href="/"' in resp.data
    assert b'href="/info"' in resp.data
