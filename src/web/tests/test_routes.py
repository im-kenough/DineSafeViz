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
    assert b"DineSafe Information" in resp.data
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
