"""DineSafe data producer and mirror: Toronto Open Data -> Blob -> DSV_DATA_DIR.

Runs as the dsv-data compose service (same image as dsv-init-db):
  python3 data.py fetch [--historical]   VM only: download, validate, upload
  python3 data.py sync                   mirror the Blob container locally

scripts/data.sh mounts a bearer token for https://storage.azure.com/ at
DSV_TOKEN_FILE. The token never comes from IMDS inside the container.
"""

import argparse
import base64
import csv
import datetime
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, urlretrieve

from refresh import (
    HISTORICAL_COLUMN_MAP,
    HISTORICAL_DIR,
    MANIFEST_NAME,
    RECENT_COLUMN_MAP,
    RECENT_NAME,
    decode_csv,
)

RECENT_CSV_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/"
    "af0f5b8a-4b73-4a50-8781-65e949792b40/download/dinesafe.csv"
)

HISTORICAL_ZIP_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/"
    "c0a5f6b0-534a-47c3-867d-d4b5cc84a656/download/"
    "Dinesafe%20Historical%20Data.zip"
)

# Sanity floors, well under today's counts (about 120,000 recent rows and
# at least 6,000 rows per historical year), so a truncated download fails.
MIN_RECENT_ROWS = 50000
MIN_HISTORICAL_ROWS = 1000

API_VERSION = "2023-11-03"


class DataError(Exception):
    """A fetch or sync problem that should stop the run with a message."""


def md5_b64(path):
    """Return the base64 MD5 of a file, the encoding Blob uses for Content-MD5."""
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode()


def validate_csv(path, column_map, min_rows):
    """Check headers and row count; return the row count or raise DataError."""
    name = os.path.basename(path)
    with open(path, "rb") as f:
        try:
            text = decode_csv(f.read())
        except UnicodeDecodeError as e:
            raise DataError(f"{name}: not UTF-8 or cp1252 ({e})") from e
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    missing = [c for c in column_map if c not in header]
    if missing:
        raise DataError(f"{name}: missing columns {', '.join(missing)}")
    rows = sum(1 for _ in reader)
    if rows < min_rows:
        raise DataError(f"{name}: {rows} rows, expected at least {min_rows}")
    return rows


class BlobStore:
    """Minimal Blob REST client authorized with a Microsoft Entra bearer token."""

    def __init__(self, account, container, token, opener=urlopen):
        self.base = f"https://{account}.blob.core.windows.net/{container}/"
        self.token = token
        self.opener = opener

    def _request(self, method, name, data=None, headers=None):
        req = Request(self.base + name, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("x-ms-version", API_VERSION)
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            return self.opener(req, timeout=120)
        except HTTPError as e:
            if e.code == 404:
                return None
            raise DataError(f"{method} {name}: HTTP {e.code}") from e
        except URLError as e:
            raise DataError(f"{method} {name}: {e.reason}") from e

    def get_md5(self, name):
        resp = self._request("HEAD", name)
        if resp is None:
            return None
        with resp:
            return resp.headers.get("Content-MD5")

    def download_to(self, name, path):
        resp = self._request("GET", name)
        if resp is None:
            raise DataError(f"{name} isn't in the container")
        with resp, open(path, "wb") as out:
            shutil.copyfileobj(resp, out)

    def upload(self, name, path, md5):
        with open(path, "rb") as f:
            body = f.read()
        content_type = "application/json" if name.endswith(".json") else "text/csv"
        resp = self._request("PUT", name, data=body, headers={
            "x-ms-blob-type": "BlockBlob",
            "Content-MD5": md5,
            "Content-Type": content_type,
        })
        if resp is None:
            raise DataError(f"PUT {name}: container not found")
        resp.close()

    def read_manifest(self):
        resp = self._request("GET", MANIFEST_NAME)
        if resp is None:
            return None
        with resp:
            return json.loads(resp.read())

    def write_manifest(self, manifest, staging_dir):
        path = os.path.join(staging_dir, MANIFEST_NAME)
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)
        self.upload(MANIFEST_NAME, path, md5_b64(path))


def _entry(name, path, rows):
    return {"name": name, "md5": md5_b64(path), "size": os.path.getsize(path), "rows": rows}


def _is_historical(entry):
    return entry["name"].startswith(HISTORICAL_DIR + "/")


def fetch(store, data_dir, historical, download=urlretrieve, now=None):
    """Download from Toronto Open Data, validate, upload changes, then the manifest.

    Historical CSVs are downloaded only when historical is True or the
    current manifest has none; otherwise their entries are carried over.
    Nothing is uploaded unless every downloaded file validates.
    """
    staging = os.path.join(data_dir, ".staging")
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(os.path.join(staging, HISTORICAL_DIR))
    try:
        remote = store.read_manifest() or {"files": []}
        carried = [e for e in remote["files"] if _is_historical(e)]
        staged = []  # (blob name, local path, row count)

        recent_path = os.path.join(staging, RECENT_NAME)
        print(f"Downloading {RECENT_CSV_URL} ...")
        download(RECENT_CSV_URL, recent_path)
        staged.append((RECENT_NAME, recent_path,
                       validate_csv(recent_path, RECENT_COLUMN_MAP, MIN_RECENT_ROWS)))

        if historical or not carried:
            carried = []
            zip_path = os.path.join(staging, "historical.zip")
            print(f"Downloading {HISTORICAL_ZIP_URL} ...")
            download(HISTORICAL_ZIP_URL, zip_path)
            with zipfile.ZipFile(zip_path) as zf:
                for member in zf.namelist():
                    base = os.path.basename(member)
                    if not base.endswith(".csv"):
                        continue
                    path = os.path.join(staging, HISTORICAL_DIR, base)
                    with zf.open(member) as src, open(path, "wb") as out:
                        shutil.copyfileobj(src, out)
                    staged.append((f"{HISTORICAL_DIR}/{base}", path,
                                   validate_csv(path, HISTORICAL_COLUMN_MAP, MIN_HISTORICAL_ROWS)))

        entries = []
        for name, path, rows in staged:
            entry = _entry(name, path, rows)
            if store.get_md5(name) == entry["md5"]:
                print(f"  {name}: unchanged")
            else:
                store.upload(name, path, entry["md5"])
                print(f"  {name}: uploaded ({rows} rows)")
            entries.append(entry)

        now = now or datetime.datetime.now(datetime.timezone.utc)
        manifest = {
            "fetched_at": now.isoformat(timespec="seconds"),
            "source_url": {"recent": RECENT_CSV_URL, "historical": HISTORICAL_ZIP_URL},
            "files": sorted(entries + carried, key=lambda e: e["name"]),
        }
        store.write_manifest(manifest, staging)
        print(f"Fetch complete: {len(manifest['files'])} files in the manifest.")
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def sync(store, data_dir):
    """Mirror the container's manifest files into data_dir, verifying MD5s.

    Each file is downloaded to <name>.part and renamed only after its MD5
    matches, so a failed sync leaves the previous files in place. CSVs not
    in the manifest are removed so the loader never reads them. The local
    manifest.json is written last.
    """
    os.makedirs(os.path.join(data_dir, HISTORICAL_DIR), exist_ok=True)
    manifest = store.read_manifest()
    if manifest is None:
        raise DataError(f"{MANIFEST_NAME} isn't in the container. Run fetch on the VM first.")

    wanted = set()
    for entry in manifest["files"]:
        name = entry["name"]
        wanted.add(os.path.normpath(name))
        local = os.path.join(data_dir, name)
        if os.path.exists(local) and md5_b64(local) == entry["md5"]:
            continue
        part = local + ".part"
        try:
            store.download_to(name, part)
            if md5_b64(part) != entry["md5"]:
                raise DataError(f"{name}: MD5 doesn't match the manifest")
            os.replace(part, local)
            print(f"  {name}: updated")
        finally:
            if os.path.exists(part):
                os.remove(part)

    for root, _dirs, files in os.walk(data_dir):
        for f in files:
            rel = os.path.normpath(os.path.relpath(os.path.join(root, f), data_dir))
            if f.endswith(".csv") and rel not in wanted:
                os.remove(os.path.join(root, f))
                print(f"  {rel}: removed (not in the manifest)")

    tmp = os.path.join(data_dir, MANIFEST_NAME + ".part")
    with open(tmp, "w") as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp, os.path.join(data_dir, MANIFEST_NAME))
    print(f"Sync complete: {len(manifest['files'])} files.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    fetch_p = sub.add_parser("fetch", help="Toronto Open Data -> Blob (VM only)")
    fetch_p.add_argument("--historical", action="store_true",
                         help="re-download the historical ZIP")
    sub.add_parser("sync", help="Blob -> DSV_DATA_DIR")
    args = parser.parse_args(argv)

    data_dir = os.environ.get("DSV_DATA_DIR", "/data")
    account = os.environ.get("DSV_STORAGE_ACCOUNT", "").strip()
    container = os.environ.get("DSV_STORAGE_CONTAINER", "dinesafe")
    token_file = os.environ.get("DSV_TOKEN_FILE", "/run/secrets/storage-token")
    try:
        if not account:
            raise DataError("DSV_STORAGE_ACCOUNT isn't set")
        try:
            with open(token_file) as f:
                token = f.read().strip()
        except OSError as e:
            raise DataError(f"can't read the storage token at {token_file}: {e.strerror}") from e
        store = BlobStore(account, container, token)
        if args.command == "fetch":
            fetch(store, data_dir, args.historical)
        else:
            sync(store, data_dir)
    except DataError as e:
        print(f"data: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
