from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import app as app_module


def _reset_cache():
    app_module._stats_cache["data"] = None
    app_module._stats_cache["fetched_at"] = None


def _mock_stats_db(total, min_date, max_date):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchone.return_value = (total, min_date, max_date)
    return mock_conn, mock_cur


def test_get_home_stats_fetches_and_caches_results():
    _reset_cache()
    now = datetime(2026, 5, 7, 12, 0, 0)
    mock_conn, mock_cur = _mock_stats_db(12345, date(2001, 1, 1), date(2025, 12, 31))

    with patch("app.psycopg2.connect", return_value=mock_conn), patch("app.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        stats = app_module._get_home_stats()

    assert stats == {
        "total_inspections": 12345, "years_of_data": 25,
        "min_date": date(2001, 1, 1), "max_date": date(2025, 12, 31),
    }
    assert app_module._stats_cache["data"] == stats
    assert app_module._stats_cache["fetched_at"] == now
    assert mock_cur.execute.call_count == 1
    assert "COUNT(DISTINCT inspection_id)" in mock_cur.execute.call_args.args[0]
    mock_conn.close.assert_called_once()
    mock_cur.close.assert_called_once()


def test_get_home_stats_uses_cache_within_ttl():
    now = datetime(2026, 5, 7, 12, 0, 0)
    app_module._stats_cache["data"] = {"total_inspections": 77, "years_of_data": 9}
    app_module._stats_cache["fetched_at"] = now - timedelta(days=1)

    with patch("app.psycopg2.connect") as mock_connect, patch("app.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        stats = app_module._get_home_stats()

    assert stats == {"total_inspections": 77, "years_of_data": 9}
    mock_connect.assert_not_called()


def test_get_home_stats_refreshes_expired_cache():
    now = datetime(2026, 5, 7, 12, 0, 0)
    app_module._stats_cache["data"] = {"total_inspections": 10, "years_of_data": 1}
    app_module._stats_cache["fetched_at"] = now - app_module._STATS_TTL - timedelta(seconds=1)
    mock_conn, _ = _mock_stats_db(54321, date(2010, 6, 1), date(2026, 1, 10))

    with patch("app.psycopg2.connect", return_value=mock_conn), patch("app.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        stats = app_module._get_home_stats()

    assert stats["total_inspections"] == 54321
    assert stats["years_of_data"] == 17


def test_get_home_stats_does_not_cache_empty_table():
    """An empty table (seed still running) must not be cached, so the next request picks up the seed."""
    _reset_cache()
    mock_conn, _ = _mock_stats_db(0, None, None)

    with patch("app.psycopg2.connect", return_value=mock_conn):
        stats = app_module._get_home_stats()

    assert stats["total_inspections"] == 0
    assert app_module._stats_cache["fetched_at"] is None


def test_home_route_renders_stats(client):
    stats = {
        "total_inspections": 12345, "years_of_data": 25,
        "min_date": date(2001, 1, 1), "max_date": date.today(),
    }
    with patch("app._get_home_stats", return_value=stats):
        resp = client.get("/")

    assert resp.status_code == 200
    assert b"Find restaurants that pass inspection" in resp.data
    assert b"12,345" in resp.data
    assert b"over 25 years" in resp.data
    assert b'href="/inspections"' in resp.data
