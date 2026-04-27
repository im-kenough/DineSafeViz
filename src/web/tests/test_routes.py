import sys
import os
from datetime import date
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module


def _mock_db(rows):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = rows
    return mock_conn


def test_route_returns_200():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert resp.status_code == 200


def test_route_renders_day_boxes():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=2024&q=1")
    assert b"day-box" in resp.data


def test_route_shows_inspection_data():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
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


def test_route_invalid_params_returns_200():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=1900&q=99")
    assert resp.status_code == 200


def test_route_no_data_day_shows_no_data_text():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/?year=2024&q=1")
    assert b"No data" in resp.data


def test_severity_class_on_row():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
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
