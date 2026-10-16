"""Test doubles for psycopg2 connections."""
from unittest.mock import MagicMock

from psycopg2.extensions import TRANSACTION_STATUS_IDLE


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
