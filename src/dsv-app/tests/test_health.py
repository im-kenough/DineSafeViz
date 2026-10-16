import threading
from unittest.mock import MagicMock, patch

import psycopg2
import psycopg2.errors
import pytest
from psycopg2.extensions import TRANSACTION_STATUS_INTRANS

import app as app_module
from db_fakes import fake_conn


def _dropped_connection(conn):
    """execute() side effect mimicking psycopg2 when the server has gone away."""
    def boom(*args, **kwargs):
        conn.closed = 2
        raise psycopg2.OperationalError("server closed the connection unexpectedly")
    return boom


def test_healthz_returns_200(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.data == b"ok"


def test_readyz_returns_200_when_db_ok(client):
    mock_cursor = MagicMock()
    mock_conn = fake_conn(mock_cursor)
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


def test_pooled_connections_are_autocommit(client):
    mock_conn = fake_conn()
    with patch("app.psycopg2.connect", return_value=mock_conn):
        assert client.get("/readyz").status_code == 200
    assert mock_conn.autocommit is True
    mock_conn.rollback.assert_not_called()


def test_pool_reuses_connection_across_requests(client):
    mock_conn = fake_conn()
    with patch("app.psycopg2.connect", return_value=mock_conn) as mock_connect:
        assert client.get("/readyz").status_code == 200
        assert client.get("/readyz").status_code == 200
        assert client.get("/inspections/month?year=2024&m=2").status_code == 200
    assert mock_connect.call_count == 1
    mock_conn.close.assert_not_called()


def test_pool_keeps_all_concurrent_connections_open():
    """All maxconn connections stay idle after a burst, not just one (psycopg2.pool's minconn)."""
    conns = [fake_conn() for _ in range(app_module.POOL_MAXCONN)]
    with patch("app.psycopg2.connect", side_effect=conns) as mock_connect:
        for _ in range(2):  # the second burst must reuse every connection
            held = [app_module._db_cursor() for _ in conns]
            for cm in held:
                cm.__enter__()
            for cm in held:
                cm.__exit__(None, None, None)
    assert mock_connect.call_count == app_module.POOL_MAXCONN
    for conn in conns:
        conn.close.assert_not_called()


def test_pool_discards_closed_connection_and_reconnects(client):
    stale_conn = fake_conn()
    fresh_conn = fake_conn()
    with patch("app.psycopg2.connect", side_effect=[stale_conn, fresh_conn]) as mock_connect:
        assert client.get("/readyz").status_code == 200
        stale_conn.closed = 1
        assert client.get("/readyz").status_code == 200
    assert mock_connect.call_count == 2
    stale_conn.close.assert_called_once()
    fresh_conn.close.assert_not_called()


def test_pool_discards_every_dead_idle_connection():
    """After a DB restart, every dead idle connection is skipped, not just the first."""
    dead = [fake_conn(), fake_conn()]
    fresh = fake_conn()
    with patch("app.psycopg2.connect", side_effect=[*dead, fresh]):
        first, second = app_module._db_cursor(), app_module._db_cursor()
        first.__enter__()
        second.__enter__()
        first.__exit__(None, None, None)
        second.__exit__(None, None, None)
        for conn in dead:
            conn.closed = 1
        with app_module._db_cursor() as cur:
            assert cur.conn is fresh
    for conn in dead:
        conn.close.assert_called_once()


def test_pool_retries_once_when_idle_connection_dies_on_execute(client):
    stale_cur = MagicMock()
    stale_conn = fake_conn(stale_cur)
    fresh_cur = MagicMock()
    fresh_conn = fake_conn(fresh_cur)

    with patch("app.psycopg2.connect", side_effect=[stale_conn, fresh_conn]) as mock_connect:
        assert client.get("/readyz").status_code == 200
        # Simulate dsv-db restart: conn.closed is still 0 until execute() hits the dead socket.
        stale_cur.execute.side_effect = _dropped_connection(stale_conn)
        assert client.get("/readyz").status_code == 200

    assert mock_connect.call_count == 2
    stale_conn.close.assert_called_once()
    fresh_cur.execute.assert_called_once_with("SELECT 1")
    fresh_conn.close.assert_not_called()


def test_statement_timeout_is_not_retried():
    mock_cur = MagicMock()
    mock_cur.execute.side_effect = psycopg2.errors.QueryCanceled("canceling statement due to statement timeout")
    mock_conn = fake_conn(mock_cur)
    with patch("app.psycopg2.connect", return_value=mock_conn) as mock_connect:
        with pytest.raises(psycopg2.errors.QueryCanceled):
            with app_module._db_cursor() as cur:
                cur.execute("SELECT pg_sleep(11)")
    assert mock_connect.call_count == 1
    assert mock_cur.execute.call_count == 1
    # The connection is still healthy, so it goes back to the pool.
    mock_conn.close.assert_not_called()


def test_operational_error_on_live_connection_is_not_retried():
    mock_cur = MagicMock()
    mock_cur.execute.side_effect = psycopg2.OperationalError("some query-level failure")
    mock_conn = fake_conn(mock_cur)
    with patch("app.psycopg2.connect", return_value=mock_conn) as mock_connect:
        with pytest.raises(psycopg2.OperationalError):
            with app_module._db_cursor() as cur:
                cur.execute("SELECT 1")
    assert mock_connect.call_count == 1
    assert mock_cur.execute.call_count == 1


def test_connection_left_mid_transaction_is_discarded():
    mock_conn = fake_conn()
    mock_conn.get_transaction_status.return_value = TRANSACTION_STATUS_INTRANS
    with patch("app.psycopg2.connect", return_value=mock_conn):
        with app_module._db_cursor() as cur:
            cur.execute("SELECT 1")
    mock_conn.close.assert_called_once()


@pytest.mark.parametrize("failure", ["cursor", "cursor_close"])
def test_cursor_failures_do_not_leak_connections(failure):
    """More failures than POOL_MAXCONN must not exhaust the pool."""
    attempts = app_module.POOL_MAXCONN + 2
    conns = [fake_conn() for _ in range(attempts + 1)]
    for conn in conns[:attempts]:
        if failure == "cursor":
            conn.cursor.side_effect = psycopg2.InterfaceError("cursor failed")
        else:
            conn.cursor.return_value.close.side_effect = psycopg2.InterfaceError("close failed")

    with patch("app.psycopg2.connect", side_effect=conns):
        for _ in range(attempts):
            with pytest.raises(psycopg2.InterfaceError):
                with app_module._db_cursor() as cur:
                    cur.execute("SELECT 1")
        # Pool still has capacity: a healthy connection can be checked out.
        with app_module._db_cursor() as cur:
            cur.execute("SELECT 1")

    for conn in conns[:attempts]:
        conn.close.assert_called_once()
    assert app_module._pool._size == 1


def test_failed_connect_releases_pool_slot():
    attempts = app_module.POOL_MAXCONN + 2
    with patch("app.psycopg2.connect", side_effect=psycopg2.OperationalError("down")):
        for _ in range(attempts):
            with pytest.raises(psycopg2.OperationalError):
                with app_module._db_cursor():
                    pass
    assert app_module._pool._size == 0


def test_pool_exhaustion_raises_pool_error():
    conns = [fake_conn() for _ in range(app_module.POOL_MAXCONN)]
    with patch("app.psycopg2.connect", side_effect=conns):
        held = [app_module._db_cursor() for _ in conns]
        for cm in held:
            cm.__enter__()
        with pytest.raises(psycopg2.pool.PoolError):
            app_module._db_cursor().__enter__()
        for cm in held:
            cm.__exit__(None, None, None)


def test_readyz_passes_1s_connect_timeout_when_pool_opens_new_connection(client):
    first_conn = fake_conn()
    second_conn = fake_conn()
    with patch("app.psycopg2.connect", side_effect=[first_conn, second_conn]) as mock_connect:
        # Pool first created by a normal 5s-timeout route.
        assert client.get("/inspections/month?year=2024&m=2").status_code == 200
        assert mock_connect.call_args.kwargs["connect_timeout"] == 5
        # Pooled connection dies; /readyz must open the replacement with connect_timeout=1.
        first_conn.closed = 1
        assert client.get("/readyz").status_code == 200
        assert mock_connect.call_args.kwargs["connect_timeout"] == 1


def test_slow_connect_does_not_block_readyz(client):
    """A page thread stuck in connect() must not hold a lock that /readyz needs."""
    connecting = threading.Event()
    release = threading.Event()
    readyz_conn = fake_conn()

    def connect(**kwargs):
        if kwargs["connect_timeout"] == 5:
            connecting.set()
            release.wait(5)
            raise psycopg2.OperationalError("timeout expired")
        return readyz_conn

    with patch("app.psycopg2.connect", side_effect=connect):
        app_module._get_pool()  # create the pool before racing threads
        slow = threading.Thread(target=lambda: app_module._get_home_stats_or_none())
        app_module._stats_cache["fetched_at"] = None
        slow.start()
        assert connecting.wait(2)
        try:
            resp = client.get("/readyz")
        finally:
            release.set()
            slow.join(5)
    assert resp.status_code == 200


def test_pool_sized_to_gunicorn_threads():
    assert app_module.POOL_MAXCONN == 4
