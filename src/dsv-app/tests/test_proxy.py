from unittest.mock import patch, MagicMock


def _mock_analytics_response(status_code=200, content=b"analytics html", headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = headers or {"Content-Type": "text/html"}
    return resp


def test_analytics_proxy_forwards_get(client):
    mock_resp = _mock_analytics_response()
    with patch("app._analytics_session.request", return_value=mock_resp) as mock_req:
        resp = client.get("/analytics/d/dinesafe/dinesafe-inspections")
    mock_req.assert_called_once()
    kwargs = mock_req.call_args.kwargs
    assert kwargs["method"] == "GET"
    assert "dsv-analytics:3000/analytics/d/dinesafe/dinesafe-inspections" in kwargs["url"]
    assert resp.status_code == 200
    assert resp.data == b"analytics html"


def test_analytics_proxy_passes_query_string(client):
    mock_resp = _mock_analytics_response()
    with patch("app._analytics_session.request", return_value=mock_resp) as mock_req:
        resp = client.get("/analytics/d/dinesafe/x?kiosk&orgId=1")
    url = mock_req.call_args.kwargs["url"]
    assert "kiosk" in url
    assert "orgId=1" in url


def test_analytics_proxy_returns_analytics_status_code(client):
    mock_resp = _mock_analytics_response(status_code=404, content=b"not found")
    with patch("app._analytics_session.request", return_value=mock_resp):
        resp = client.get("/analytics/nonexistent")
    assert resp.status_code == 404


def test_analytics_proxy_forwards_post(client):
    mock_resp = _mock_analytics_response(
        content=b'{"results":{}}',
        headers={"Content-Type": "application/json"},
    )
    payload = b'{"queries":[]}'
    with patch("app._analytics_session.request", return_value=mock_resp) as mock_req:
        resp = client.post(
            "/analytics/api/ds/query",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
    kwargs = mock_req.call_args.kwargs
    assert kwargs["method"] == "POST"
    assert kwargs["data"] == payload
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert resp.status_code == 200
    assert resp.data == b'{"results":{}}'
