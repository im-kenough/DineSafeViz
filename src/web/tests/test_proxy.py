import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module


def _mock_grafana_response(status_code=200, content=b"grafana html",
                           headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = headers or {"Content-Type": "text/html"}
    return resp


def test_grafana_proxy_forwards_get():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    mock_resp = _mock_grafana_response()
    with patch("app.http_requests.request", return_value=mock_resp) as mock_req:
        resp = client.get("/grafana/d/dinesafe/dinesafe-inspections")
    mock_req.assert_called_once()
    kwargs = mock_req.call_args.kwargs
    assert kwargs["method"] == "GET"
    assert "grafana:3000/grafana/d/dinesafe/dinesafe-inspections" in kwargs["url"]
    assert resp.status_code == 200
    assert resp.data == b"grafana html"


def test_grafana_proxy_passes_query_string():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    mock_resp = _mock_grafana_response()
    with patch("app.http_requests.request", return_value=mock_resp) as mock_req:
        resp = client.get("/grafana/d/dinesafe/x?kiosk&orgId=1")
    url = mock_req.call_args.kwargs["url"]
    assert "kiosk" in url
    assert "orgId=1" in url


def test_grafana_proxy_returns_grafana_status_code():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    mock_resp = _mock_grafana_response(status_code=404, content=b"not found")
    with patch("app.http_requests.request", return_value=mock_resp):
        resp = client.get("/grafana/nonexistent")
    assert resp.status_code == 404
