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
import loader
from data import BlobStore, DataError
from dinesafe_csv import RECENT_NAME


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Arbitrary advisory lock key. load() holds it for its whole transaction, so
# a deploy's load and the timer's load can't both seed or both refresh: the
# second waits, then sees the first one's load_log row.
LOAD_LOCK = 0x44535640AD


# ---------------------------------------------------------------------------
# Load logic
# ---------------------------------------------------------------------------

def decide(table_empty, loaded, newest, force):
    """Pick the load action. loaded is (recent path of the last load,
    historical path of the last seed); newest is (newest recent file,
    newest complete historical folder) in Blob.

    Seed an empty table, or reseed when Blob has a historical folder the
    last seed didn't use. Otherwise refresh unless the newest recent file is
    already loaded.
    """
    last_recent, last_historical = loaded
    newest_recent, newest_historical = newest
    if table_empty or (newest_historical is not None and newest_historical != last_historical):
        return "seed"
    if force or last_recent != newest_recent:
        return "refresh"
    return "skip"


def _download_each(store, names, tmp):
    """Yield a local path for each blob, downloading it just before it's
    read and deleting it after, so /tmp holds one historical file at a time."""
    for name in names:
        path = os.path.join(tmp, os.path.basename(name))
        store.download_to(name, path)
        yield path
        os.remove(path)


def load(store, conn, force=False):
    """Load the newest raw-zone files into Postgres, in one transaction.

    Downloads into a temp directory, runs the seed or refresh, records the
    load in load_log, and commits. On any error nothing is committed.
    Returns "seed", "refresh", or "skip".
    """
    recent_path, _ = data.require_newest_recent(store)
    historical_path, historical_names = data.newest_historical(store) or (None, None)
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (LOAD_LOCK,))
    action = decide(loader.is_empty(conn), loader.last_load(conn), (recent_path, historical_path), force)
    if action == "skip":
        print(f"Already current: {recent_path} is loaded.")
        conn.rollback()  # releases the lock
        return action
    if action == "seed" and historical_path is None:
        raise DataError(
            f"{data.HISTORICAL_PREFIX} has no complete folder. "
            "Run: scripts/pipeline.sh <env> ingest --historical"
        )

    with tempfile.TemporaryDirectory() as tmp:
        recent_csv = os.path.join(tmp, RECENT_NAME)
        store.download_to(recent_path, recent_csv)
        if action == "seed":
            print(f"Seeding from {historical_path} and {recent_path} ...")
            deleted, inserted = loader.seed(conn, recent_csv, _download_each(store, historical_names, tmp))
        else:
            deleted, inserted = loader.refresh(conn, recent_csv)
    # Only seeds record a historical folder.
    loader.record_load(conn, action, recent_path,
                       historical_path if action == "seed" else None, deleted, inserted)
    conn.commit()
    print(f"{action.capitalize()} complete from {recent_path}: "
          f"deleted {deleted}, inserted {inserted} rows.")
    return action


# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

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
            conn = (connect or loader.get_connection)()
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
