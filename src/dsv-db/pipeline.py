"""DineSafe data pipeline: Toronto Open Data -> Blob raw zone -> Postgres.

Runs as the dsv-pipeline Compose service, through scripts/pipeline.sh:
  python3 pipeline.py ingest [--force] [--historical]   Toronto Open Data -> Blob
  python3 pipeline.py load [--force]                    Blob -> inspections
  python3 pipeline.py run [--force] [--historical]      ingest, load, staleness check

pipeline.sh mounts a bearer token for https://storage.azure.com/ at
DSV_TOKEN_FILE. load never contacts Toronto Open Data. Exit codes: 0
success, 1 failure, 2 usage.
"""

import argparse
import os
import sys
import tempfile

import psycopg2

import data
import refresh
from data import BlobStore, DataError

# Arbitrary advisory lock key. load() holds it for its whole transaction, so
# a deploy's load and the timer's load can't both seed or both refresh: the
# second waits, then sees the first one's load_log row.
LOAD_LOCK = 0x44535640AD


def decide(table_empty, last_loaded, newest, force):
    """Seed an empty table; otherwise refresh unless newest is already loaded."""
    if table_empty:
        return "seed"
    if force or last_loaded != newest:
        return "refresh"
    return "skip"


def load(store, conn, force=False):
    """Load the newest raw-zone files into Postgres, in one transaction.

    Downloads into a temp directory laid out the way refresh.py reads it,
    runs the seed or refresh, records the load in load_log, and commits.
    On any error nothing is committed. Returns "seed", "refresh", or "skip".
    """
    newest = data.newest_recent(store)
    if newest is None:
        raise DataError("recent/ is empty. Run ingest first: scripts/pipeline.sh <env> ingest")
    recent_path = newest[0]
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (LOAD_LOCK,))
    action = decide(refresh.is_empty(conn), refresh.last_loaded_path(conn), recent_path, force)
    if action == "skip":
        print(f"Already current: {recent_path} is loaded.")
        conn.rollback()  # releases the lock
        return action

    historical_path = None
    with tempfile.TemporaryDirectory() as tmp:
        store.download_to(recent_path, os.path.join(tmp, refresh.RECENT_NAME))
        if action == "seed":
            historical = data.newest_historical(store)
            if historical is None:
                raise DataError(
                    "historical/ has no complete folder. Run: scripts/pipeline.sh <env> ingest --historical"
                )
            historical_path, names = historical
            hist_dir = os.path.join(tmp, refresh.HISTORICAL_DIR)
            os.makedirs(hist_dir)
            for name in names:
                store.download_to(name, os.path.join(hist_dir, os.path.basename(name)))
            deleted, inserted = refresh.seed(conn, tmp)
        else:
            deleted, inserted = refresh.refresh(conn, tmp)
    refresh.record_load(conn, action, recent_path, historical_path, deleted, inserted)
    conn.commit()
    print(f"{action.capitalize()} complete from {recent_path}: "
          f"deleted {deleted}, inserted {inserted} rows.")
    return action


def _store_from_env():
    account = os.environ.get("DSV_STORAGE_ACCOUNT", "").strip()
    container = os.environ.get("DSV_STORAGE_CONTAINER", "dinesafe")
    token_file = os.environ.get("DSV_TOKEN_FILE", "/run/secrets/storage-token")
    if not account:
        raise DataError("DSV_STORAGE_ACCOUNT isn't set")
    try:
        with open(token_file) as f:
            token = f.read().strip()
    except OSError as e:
        raise DataError(f"can't read the storage token at {token_file}: {e.strerror}") from e
    return BlobStore(account, container, token)


def main(argv=None, store_factory=None, connect=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("ingest", "Toronto Open Data -> Blob"),
                            ("run", "ingest, load, then the staleness check")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--force", action="store_true",
                       help="download even if Toronto's last_modified isn't newer")
        p.add_argument("--historical", action="store_true",
                       help="download the historical ZIP again")
    load_p = sub.add_parser("load", help="Blob -> inspections")
    load_p.add_argument("--force", action="store_true",
                        help="reload the newest file even if it's already loaded")
    args = parser.parse_args(argv)

    conn = None
    try:
        store = (store_factory or _store_from_env)()
        if args.command in ("ingest", "run"):
            data.ingest(store, force=args.force, historical=args.historical)
        if args.command in ("load", "run"):
            conn = (connect or refresh.get_connection)()
            load(store, conn, force=args.force if args.command == "load" else False)
        if args.command == "run":
            data.check_fresh(store)
    except (DataError, psycopg2.Error) as e:
        print(f"pipeline: {e}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()  # closing without commit rolls back
    return 0


if __name__ == "__main__":
    sys.exit(main())
