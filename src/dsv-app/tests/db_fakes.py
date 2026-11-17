"""Test doubles for psycopg2 connections, and the rows they return."""
from datetime import date
from unittest.mock import MagicMock

from psycopg2.extensions import TRANSACTION_STATUS_IDLE

EST_ID = "001Vo000013QjdPIAS"


def inspection_row(day=date(2024, 2, 14), status="Pass", details=None, severity=None,
                   name="Pizza Pizza", street="123 Queen St W", unit=None, **columns):
    """One row as app._INSPECTION_SELECT returns it (the /inspections and
    restaurant page queries). columns overrides any other column by name."""
    return {
        "inspection_date": day,
        "establishment_status": status,
        "action": None,
        "infraction_details": details,
        "establishment_name": name,
        "establishment_address": f"{street} M5V 2A1",
        "establishment_type": None,
        "street": street,
        "unit": unit,
        "postal_code": None,
        "latitude": None,
        "longitude": None,
        "outcome": None,
        "outcome_date": None,
        "amount_fined": None,
        "establishment_id": EST_ID,
        "severity": severity,
        "infraction_category": None,
    } | columns


def search_row(n=1, name="Pizza Pizza", status="Pass", est_type=None, unit=None):
    """One row as the search page query returns it."""
    return {
        "establishment_id": f"001Vo0000000000{n:03d}",
        "establishment_name": name,
        "street": "123 Queen St W",
        "unit": unit,
        "establishment_status": status,
        "last_inspected": date(2026, 10, 3),
        "inspection_count": 14,
        "first_inspected": date(2019, 3, 4),
        "establishment_type": est_type,
    }


def fake_conn(cursor=None):
    """A MagicMock shaped like an open, idle psycopg2 connection.

    A bare MagicMock() has a truthy ``closed`` attribute, so the pool would treat it
    as dead. Set ``conn.closed = 1`` (or 2) in a test to simulate a dropped connection.
    """
    conn = MagicMock()
    conn.closed = 0
    conn.get_transaction_status.return_value = TRANSACTION_STATUS_IDLE
    if cursor is not None:
        conn.cursor.return_value = cursor
    return conn


def rows_conn(rows):
    """A fake connection whose cursor's fetchall() returns rows."""
    conn = fake_conn()
    conn.cursor.return_value.fetchall.return_value = rows
    return conn


def search_conn(rows, total=None, pins=()):
    """A fake connection answering /search: the count query's fetchone(), then
    fetchall() for the map pins, then fetchall() for the page.

    total defaults to len(rows), as for a search with one page of results.
    """
    conn = fake_conn()
    cur = conn.cursor.return_value
    cur.fetchone.return_value = {"total": len(rows) if total is None else total}
    cur.fetchall.side_effect = [list(pins), rows]
    return conn


def stats_conn(total, min_date, max_date):
    """A fake connection answering the home-stats query with one row."""
    conn = fake_conn()
    conn.cursor.return_value.fetchone.return_value = (total, min_date, max_date)
    return conn
