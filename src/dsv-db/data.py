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
