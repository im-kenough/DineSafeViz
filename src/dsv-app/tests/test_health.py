from unittest.mock import MagicMock, patch

import psycopg2

import app as app_module


def test_healthz_returns_200(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.data == b"ok"


def test_readyz_returns_200_when_db_ok(client):
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch("app.psycopg2.connect", return_value=mock_conn) as mock_connect:
        resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.data == b"ok"
    mock_cursor.execute.assert_called_once_with("SELECT 1")
    assert mock_connect.call_args.kwargs["connect_timeout"] == 1


def test_readyz_returns_503_when_db_fails(client):
    with patch("app.psycopg2.connect", side_effect=Exception("connection refused")):
        resp = client.get("/readyz")
    assert resp.status_code == 503


def test_pool_reuses_connection_across_requests(client):
    mock_conn = MagicMock()
    with patch("app.psycopg2.connect", return_value=mock_conn) as mock_connect:
        assert client.get("/readyz").status_code == 200
        assert client.get("/readyz").status_code == 200
        assert client.get("/inspections/month?year=2024&m=2").status_code == 200
    assert mock_connect.call_count == 1
    mock_conn.close.assert_not_called()


def test_pool_discards_closed_connection_and_reconnects(client):
    stale_conn = MagicMock()
    fresh_conn = MagicMock()
    with patch("app.psycopg2.connect", side_effect=[stale_conn, fresh_conn]) as mock_connect:
        assert client.get("/readyz").status_code == 200
        stale_conn.closed = 1
        assert client.get("/readyz").status_code == 200
    assert mock_connect.call_count == 2
    stale_conn.close.assert_called_once()
    fresh_conn.close.assert_not_called()


def test_pool_retries_once_when_idle_connection_dies_on_execute(client):
    stale_conn = MagicMock()
    stale_cur = MagicMock()
    stale_conn.cursor.return_value = stale_cur
    fresh_conn = MagicMock()
    fresh_cur = MagicMock()
    fresh_conn.cursor.return_value = fresh_cur

    with patch("app.psycopg2.connect", side_effect=[stale_conn, fresh_conn]) as mock_connect:
        assert client.get("/readyz").status_code == 200
        # Simulate dsv-db restart: conn.closed is still 0 until execute() hits the dead socket.
        stale_cur.execute.side_effect = psycopg2.OperationalError("server closed the connection unexpectedly")
        assert client.get("/readyz").status_code == 200

    assert mock_connect.call_count == 2
    stale_conn.close.assert_called_once()
    fresh_cur.execute.assert_called_once_with("SELECT 1")
    fresh_conn.close.assert_not_called()


def test_readyz_passes_1s_connect_timeout_when_pool_opens_new_connection(client):
    first_conn = MagicMock()
    second_conn = MagicMock()
    with patch("app.psycopg2.connect", side_effect=[first_conn, second_conn]) as mock_connect:
        # Pool first created by a normal 5s-timeout route.
        assert client.get("/inspections/month?year=2024&m=2").status_code == 200
        assert mock_connect.call_args.kwargs["connect_timeout"] == 5
        # Pooled connection dies; /readyz must open the replacement with connect_timeout=1.
        first_conn.closed = 1
        assert client.get("/readyz").status_code == 200
        assert mock_connect.call_args.kwargs["connect_timeout"] == 1


def test_pool_sized_to_gunicorn_threads():
    assert app_module.POOL_MINCONN == 1
    assert app_module.POOL_MAXCONN == 4


