from datetime import date
from unittest.mock import patch, MagicMock


def _mock_db(rows):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = rows
    return mock_conn


def test_home_has_dashboard_link(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/dashboard"' in resp.data
    assert b"Dashboard" in resp.data
    assert b'href="/info"' in resp.data
    assert b"Info" in resp.data


def test_info_page(client):
    resp = client.get("/info")
    assert resp.status_code == 200
    assert b"DineSafeViz Info" in resp.data
    assert b"Data Dictionary" in resp.data
    assert b"<table>" in resp.data
    assert b"Establishment ID" in resp.data


def test_route_returns_200(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert resp.status_code == 200


def test_route_renders_day_boxes(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=2024&q=1")
    assert b"day-box" in resp.data


def test_route_shows_inspection_data(client):
    rows = [(
        date(2024, 2, 14),   # inspection_date
        "C - Crucial",       # severity
        "Court Order",       # action
        "Rats observed",     # infraction_details
        "Risky Bistro",      # establishment_name
        "1 Main St",         # establishment_address
        "Pass",              # outcome
        "2024-02-20",        # outcome_date
        "500.00",            # amount_fined
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/?year=2024&q=1")
    assert b"Risky Bistro" in resp.data
    assert b"C - Crucial" in resp.data
    assert b"Rats observed" in resp.data


def test_route_invalid_params_returns_200(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=1900&q=99")
    assert resp.status_code == 200


def test_route_no_data_day_shows_no_data_text(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=2024&q=1")
    assert b"No data" in resp.data


def test_severity_class_on_row(client):
    rows = [(
        date(2024, 2, 14),   # inspection_date
        "C - Crucial",       # severity
        "Court Order",       # action
        "Rats observed",     # infraction_details
        "Risky Bistro",      # establishment_name
        "1 Main St",         # establishment_address
        "Pass",              # outcome
        "2024-02-20",        # outcome_date
        "500.00",            # amount_fined
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/?year=2024&q=1")
    assert b'class="sev-crucial"' in resp.data


def test_footer_content(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b"&copy; 2026 Kenneth Ho" in resp.data
    assert b"DineSafeViz v0.1.0" in resp.data


def test_dropdown_menu_present(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_year_and_quarter_links(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/?year=2023&q=4"' in resp.data
    assert b'href="/?year=2023&q=1"' not in resp.data
    assert b'href="/?year=2024&q=1"' in resp.data
    assert b'href="/?year=2024&q=4"' in resp.data


def test_standalone_year_tabs_removed(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/?year=2024"' not in resp.data
    assert b'href="/?year=2023"' not in resp.data


def test_dropdown_present_on_dashboard(client):
    resp = client.get("/dashboard")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_dashboard(client):
    resp = client.get("/dashboard")
    assert b'href="/?year=2023&q=4"' in resp.data
    assert b'href="/?year=2024&q=1"' in resp.data


def test_dropdown_present_on_info(client):
    resp = client.get("/info")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_info(client):
    resp = client.get("/info")
    assert b'href="/?year=2023&q=4"' in resp.data
    assert b'href="/?year=2024&q=1"' in resp.data


def test_dashboard_nav_active_class(client):
    resp = client.get("/dashboard")
    assert b'href="/dashboard" class="nav-btn active"' in resp.data


def test_info_nav_active_class(client):
    resp = client.get("/info")
    assert b'href="/info" class="nav-btn active"' in resp.data


def test_index_nav_active_class(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'class="nav-btn active">Inspections' in resp.data


def test_dropdown_has_archive_item(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'archive-item' in resp.data
    assert b'Archive' in resp.data


def test_archive_contains_old_year_links(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/?year=2022&q=1"' in resp.data


def test_recent_years_not_in_archive(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/?year=2023&q=4"' in resp.data
