import uuid
from unittest.mock import MagicMock, patch


def test_healthz_returns_200(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.data == b"ok"


def test_readyz_returns_200_when_db_ok(client):
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch("app.psycopg2.connect", return_value=mock_conn):
        resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.data == b"ok"
    mock_cursor.execute.assert_called_once_with("SELECT 1")


def test_readyz_returns_503_when_db_fails(client):
    with patch("app.psycopg2.connect", side_effect=Exception("connection refused")):
        resp = client.get("/readyz")
    assert resp.status_code == 503
