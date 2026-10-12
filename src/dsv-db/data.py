"""DineSafe raw zone: Toronto Open Data -> the Blob container.

pipeline.py uses this module. The raw zone, in the dinesafe container:
  recent/<YYYYMMDDTHHMMSSZ>/Dinesafe.csv          metadata: source_last_modified
  historical/<YYYYMMDDTHHMMSSZ>/<year>.csv         plus _SUCCESS, written last
Blobs are never overwritten. The newest folder is the last in sorted order,
because the folder names are UTC timestamps.
"""

import collections
import csv
import datetime
import hashlib
import base64
import io
import json
import os
import shutil
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from refresh import HISTORICAL_COLUMN_MAP, RECENT_COLUMN_MAP, RECENT_NAME, decode_csv

CKAN_PACKAGE_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=dinesafe"
)
# Exact names and formats. The package also lists "Dinesafe™.csv", a stale
# copy in the old schema, so a looser match would pick the wrong file.
RECENT_RESOURCE = ("Dinesafe.csv", "CSV")
HISTORICAL_RESOURCE = ("Dinesafe Historical Data", "ZIP")

RECENT_PREFIX = "recent/"
HISTORICAL_PREFIX = "historical/"
# Written after every historical file, so a half-uploaded folder is ignored.
SUCCESS_MARKER = "_SUCCESS"
KEEP_RECENT = 30

# Sanity floors, well under today's counts (about 120,000 recent rows and
# at least 6,000 rows per historical year), so a truncated download fails.
MIN_RECENT_ROWS = 50000
MIN_HISTORICAL_ROWS = 1000

API_VERSION = "2023-11-03"

# Seconds without data before a download gives up, so a stalled server
# can't hang a deploy or the timer.
DOWNLOAD_TIMEOUT = 120

BlobInfo = collections.namedtuple("BlobInfo", ["metadata", "md5"])


class DataError(Exception):
    """A raw-zone problem that should stop the run with a message."""


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


def http_download(url, path, opener=urlopen):
    """Download url to path, raising DataError on any network failure."""
    try:
        with opener(url, timeout=DOWNLOAD_TIMEOUT) as resp, open(path, "wb") as out:
            shutil.copyfileobj(resp, out)
    except OSError as e:  # URLError, HTTPError, and timeouts are all OSErrors
        raise DataError(f"download from {url} failed: {e}") from e


def resolve_resources(opener=urlopen):
    """Find the recent CSV and the historical ZIP in the CKAN package.

    Returns {"recent": {"url", "last_modified"}, "historical": {...}}.
    Looking resources up by name survives a changed resource ID, which
    happened once already, in June 2026.
    """
    try:
        with opener(CKAN_PACKAGE_URL, timeout=DOWNLOAD_TIMEOUT) as resp:
            body = resp.read()
    except OSError as e:
        raise DataError(f"CKAN package_show failed: {e}") from e
    try:
        resources = json.loads(body)["result"]["resources"]
    except (ValueError, KeyError, TypeError) as e:
        raise DataError(f"CKAN package_show didn't return the expected JSON: {e}") from e
    found = {}
    for key, (name, fmt) in (("recent", RECENT_RESOURCE), ("historical", HISTORICAL_RESOURCE)):
        matches = [r for r in resources if r.get("name") == name and r.get("format") == fmt]
        if len(matches) != 1:
            raise DataError(
                f"CKAN package has {len(matches)} resources named {name!r} ({fmt}); expected 1"
            )
        found[key] = {"url": matches[0]["url"], "last_modified": matches[0].get("last_modified") or ""}
    return found


class BlobStore:
    """Minimal Blob REST client authorized with a Microsoft Entra bearer token."""

    def __init__(self, account, container, token, opener=urlopen):
        self.container_url = f"https://{account}.blob.core.windows.net/{container}"
        self.token = token
        self.opener = opener

    def _request(self, method, url, data=None, headers=None):
        """Send one request. Returns the response, or None on HTTP 404."""
        req = Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("x-ms-version", API_VERSION)
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            return self.opener(req, timeout=DOWNLOAD_TIMEOUT)
        except HTTPError as e:
            if e.code == 404:
                return None
            raise DataError(f"{method} {url}: HTTP {e.code}") from e
        except URLError as e:
            raise DataError(f"{method} {url}: {e.reason}") from e

    def _blob_url(self, name):
        return f"{self.container_url}/{quote(name)}"

    def list(self, prefix):
        """Return {name: BlobInfo} for every blob under prefix."""
        blobs, marker = {}, ""
        while True:
            query = {"restype": "container", "comp": "list", "prefix": prefix, "include": "metadata"}
            if marker:
                query["marker"] = marker
            resp = self._request("GET", f"{self.container_url}?{urlencode(query)}")
            if resp is None:
                raise DataError(f"{self.container_url}: container not found")
            with resp:
                root = ET.fromstring(resp.read())
            for blob in root.iter("Blob"):
                meta = blob.find("Metadata")
                blobs[blob.findtext("Name")] = BlobInfo(
                    {m.tag: m.text or "" for m in meta} if meta is not None else {},
                    blob.findtext("Properties/Content-MD5") or "",
                )
            marker = root.findtext("NextMarker") or ""
            if not marker:
                return blobs

    def download_to(self, name, path):
        resp = self._request("GET", self._blob_url(name))
        if resp is None:
            raise DataError(f"{name} isn't in the container")
        with resp, open(path, "wb") as out:
            shutil.copyfileobj(resp, out)

    def upload(self, name, path, md5, metadata=None):
        with open(path, "rb") as f:
            body = f.read()
        headers = {"x-ms-blob-type": "BlockBlob", "Content-MD5": md5, "Content-Type": "text/csv"}
        for key, value in (metadata or {}).items():
            headers[f"x-ms-meta-{key}"] = value
        resp = self._request("PUT", self._blob_url(name), data=body, headers=headers)
        if resp is None:
            raise DataError(f"PUT {name}: container not found")
        resp.close()

    def delete(self, name):
        """Delete a blob. Soft delete keeps it recoverable for 7 days."""
        resp = self._request("DELETE", self._blob_url(name))
        if resp is not None:
            resp.close()


def folders(names, prefix):
    """Sorted, unique folder names directly under prefix."""
    return sorted({
        n[len(prefix):].split("/", 1)[0]
        for n in names
        if n.startswith(prefix) and "/" in n[len(prefix):]
    })


def newest_recent(store):
    """Return (blob path, BlobInfo) of the newest recent file, or None."""
    blobs = store.list(RECENT_PREFIX)
    paths = sorted(n for n in blobs if n.endswith("/" + RECENT_NAME))
    if not paths:
        return None
    return paths[-1], blobs[paths[-1]]


def newest_historical(store):
    """Return (folder path, [CSV blob names]) of the newest complete
    historical folder, or None. A folder is complete once it has _SUCCESS."""
    blobs = store.list(HISTORICAL_PREFIX)
    complete = [
        f for f in folders(blobs, HISTORICAL_PREFIX)
        if f"{HISTORICAL_PREFIX}{f}/{SUCCESS_MARKER}" in blobs
    ]
    if not complete:
        return None
    folder = f"{HISTORICAL_PREFIX}{complete[-1]}/"
    return folder, sorted(n for n in blobs if n.startswith(folder) and n.endswith(".csv"))
