from datetime import date, datetime, timedelta
from unittest.mock import patch

import app as app_module
from db_fakes import stats_conn


def test_get_home_stats_fetches_and_caches_results(empty_stats_cache):
    now = datetime(2026, 5, 7, 12, 0, 0)
    mock_conn = stats_conn(12345, date(2001, 1, 1), date(2025, 12, 31))
    mock_cur = mock_conn.cursor.return_value

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
    assert "SELECT DISTINCT establishment_id, inspection_date" in mock_cur.execute.call_args.args[0]
    mock_conn.close.assert_not_called()
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
    mock_conn = stats_conn(54321, date(2010, 6, 1), date(2026, 1, 10))

    with patch("app.psycopg2.connect", return_value=mock_conn), patch("app.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        stats = app_module._get_home_stats()

    assert stats["total_inspections"] == 54321
    assert stats["years_of_data"] == 17


def test_get_home_stats_does_not_cache_empty_table(empty_stats_cache):
    """An empty table (seed still running) must not be cached, so the next request picks up the seed."""
    mock_conn = stats_conn(0, None, None)

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


def test_home_renders_about_card(client):
    html = client.get("/").data.decode()

    card = html[html.index('<section class="day-box about"'):]
    card = card[:card.index("</section>")]
    assert 'aria-labelledby="about-heading"' in card
    assert 'href="https://github.com/im-kenough/DineSafeViz" target="_blank" rel="noopener"' in card
    assert 'href="https://kennethho.ca" target="_blank" rel="noopener"' in card
    assert "(opens in new tab)" in card
    assert "Not affiliated with the City of Toronto." in card
    # sits under Explore
    assert html.index('class="hero"') < html.index('id="explore-heading"') < html.index('id="about-heading"')
