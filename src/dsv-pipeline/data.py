"""DineSafe raw zone: Toronto Open Data -> the Blob container.

pipeline.py uses this module. The raw zone, in the dinesafe container:
  recent/<YYYYMMDDTHHMMSSZ>/Dinesafe.csv          metadata: source_last_modified
  historical/<YYYYMMDDTHHMMSSZ>/<year>.csv         plus _SUCCESS, written last
Blobs are never overwritten. The newest folder is the last in sorted order,
because the folder names are UTC timestamps.
"""

import base64
import collections
import csv
import datetime
import hashlib
import io
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from loader import HISTORICAL_COLUMN_MAP, RECENT_COLUMN_MAP, RECENT_NAME, EncodingDetector, open_csv


# ---------------------------------------------------------------------------
# Constants and configuration
# ---------------------------------------------------------------------------

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
# Blob metadata on each recent file: CKAN's last_modified when it was ingested.
SOURCE_MODIFIED_KEY = "source_last_modified"
# check_fresh fails when the newest source data is older than this.
STALE_AFTER = datetime.timedelta(days=10)

# Sanity floors, well under today's counts (about 120,000 recent rows and
# at least 6,000 rows per historical year), so a truncated download fails.
MIN_RECENT_ROWS = 50000
MIN_HISTORICAL_ROWS = 1000

API_VERSION = "2023-11-03"

# Seconds without data before a download gives up, so a stalled server
# can't hang a deploy or the timer.
DOWNLOAD_TIMEOUT = 120

# Largest historical CSV accepted from the ZIP, decompressed. Today's are a
# few MiB each; the cap stops a decompression bomb from running unbounded.
MAX_HISTORICAL_BYTES = 256 << 20

# What zipfile raises for a corrupt, truncated, or encrypted member, or an
# unsupported compression method. ZipFile() only parses the central directory,
# so these surface only once a member is opened or read.
ZIP_MEMBER_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, RuntimeError, NotImplementedError)


# ---------------------------------------------------------------------------
# Exceptions and types
# ---------------------------------------------------------------------------

BlobInfo = collections.namedtuple("BlobInfo", ["metadata", "md5"])


class DataError(Exception):
    """A raw-zone problem that should stop the run with a message."""


# ---------------------------------------------------------------------------
# HTTP and file utilities
# ---------------------------------------------------------------------------

def md5_b64(source):
    """Return the base64 MD5 of a file or binary stream, the encoding Blob uses
    for Content-MD5. A stream is read to EOF and not rewound."""
    if isinstance(source, (str, os.PathLike)):
        with open(source, "rb") as f:
            return md5_b64(f)
    digest = hashlib.md5(usedforsecurity=False)  # integrity checksum, not security
    for chunk in iter(lambda: source.read(1 << 20), b""):
        digest.update(chunk)
    return base64.b64encode(digest.digest()).decode()


def validate_csv(source, column_map, min_rows, name=None):
    """Check headers and row count of a CSV path or text stream; return the row
    count or raise DataError. A stream is read to EOF and not rewound."""
    if isinstance(source, (str, os.PathLike)):
        with open_csv(source) as f:
            return validate_csv(f, column_map, min_rows, name or os.path.basename(source))
    name = name or os.path.basename(getattr(source, "name", "<stream>"))
    try:
        reader = csv.reader(source)
        header = next(reader, [])
        missing = [c for c in column_map if c not in header]
        if missing:
            raise DataError(f"{name}: missing columns {', '.join(missing)}")
        rows = sum(1 for _ in reader)
    except UnicodeDecodeError as e:
        raise DataError(f"{name}: not UTF-8 or cp1252 ({e})") from e
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


# ---------------------------------------------------------------------------
# CKAN API
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Blob storage
# ---------------------------------------------------------------------------

class BlobStore:
    """Minimal Blob REST client authorized with a Microsoft Entra bearer token."""

    def __init__(self, account, container, token, opener=urlopen):
        self.container_url = f"https://{account}.blob.core.windows.net/{container}"
        self.token = token
        self.opener = opener

    def _request(self, method, url, data=None, headers=None):
        """Send one request. Returns the response, or None on HTTP 404."""
        # Always https://<account>.blob.core.windows.net, built in __init__.
        req = Request(url, data=data, method=method)  # noqa: S310
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
                # Authenticated HTTPS response from Azure, and Python's bundled
                # Expat (2.4.1+) already refuses entity-expansion attacks.
                root = ET.fromstring(resp.read())  # noqa: S314
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

    def upload(self, name, source, md5, metadata=None, length=None):
        # Streams a file path or binary stream. Put Blob needs Content-Length;
        # without it, urllib would send the body chunked. A stream needs an
        # explicit length, the exact number of bytes it will yield.
        if isinstance(source, (str, os.PathLike)):
            with open(source, "rb") as body:
                self.upload(name, body, md5, metadata=metadata, length=os.path.getsize(source))
            return
        if length is None:
            raise ValueError(f"upload of {name} from a stream needs a length")
        headers = {"x-ms-blob-type": "BlockBlob", "Content-MD5": md5, "Content-Type": "text/csv",
                   "Content-Length": str(length)}
        for key, value in (metadata or {}).items():
            headers[f"x-ms-meta-{key}"] = value
        resp = self._request("PUT", self._blob_url(name), data=source, headers=headers)
        if resp is None:
            raise DataError(f"PUT {name}: container not found")
        resp.close()

    def delete(self, name):
        """Delete a blob. Soft delete keeps it recoverable for 7 days."""
        resp = self._request("DELETE", self._blob_url(name))
        if resp is not None:
            resp.close()


# ---------------------------------------------------------------------------
# Blob queries
# ---------------------------------------------------------------------------

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


def require_newest_recent(store):
    """Return newest_recent(store), or raise DataError if recent/ is empty."""
    newest = newest_recent(store)
    if newest is None:
        raise DataError(f"{RECENT_PREFIX} is empty. Run ingest first: scripts/pipeline.sh <env> ingest")
    return newest


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


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def _scan_member(zf, info, name):
    """One pass over a ZIP member's bytes. Returns (encoding, md5, size).

    Counts the bytes actually decompressed, rather than trusting the header's
    file_size, and enforces MAX_HISTORICAL_BYTES.
    """
    if info.file_size > MAX_HISTORICAL_BYTES:
        raise DataError(f"{name}: {info.file_size} bytes, more than the {MAX_HISTORICAL_BYTES} limit")
    detector = EncodingDetector()
    digest = hashlib.md5(usedforsecurity=False)  # integrity checksum, not security
    size = 0
    with zf.open(info) as raw:
        for chunk in iter(lambda: raw.read(1 << 20), b""):
            size += len(chunk)
            if size > MAX_HISTORICAL_BYTES:
                raise DataError(f"{name}: more than the {MAX_HISTORICAL_BYTES} byte limit")
            digest.update(chunk)
            detector.feed(chunk)
    if size != info.file_size:
        raise DataError(f"{name}: {size} bytes decompressed, but the ZIP header says {info.file_size}")
    return detector.result(), base64.b64encode(digest.digest()).decode(), size


def _download_historical(url, tmp, download):
    """Download the historical ZIP into tmp and validate every CSV member in
    place, without extracting. Returns (zip_path, [(file name, ZipInfo, md5,
    size)]), sorted by file name."""
    zip_path = os.path.join(tmp, "historical.zip")
    print(f"Downloading {url} ...")
    download(url, zip_path)
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as e:
        raise DataError(f"historical download isn't a ZIP file: {e}") from e
    staged = {}
    with zf:
        for info in zf.infolist():
            base = os.path.basename(info.filename)
            if not base.endswith(".csv"):
                continue
            # Members are flattened into one folder, and blobs are never
            # overwritten, so two members can't share a file name.
            if base in staged:
                raise DataError(f"the historical ZIP has more than one {base}")
            try:
                encoding, md5, size = _scan_member(zf, info, base)
                with zf.open(info) as raw, io.TextIOWrapper(raw, encoding=encoding, newline="") as text:
                    validate_csv(text, HISTORICAL_COLUMN_MAP, MIN_HISTORICAL_ROWS, name=base)
            except ZIP_MEMBER_ERRORS as e:
                raise DataError(f"historical ZIP member {info.filename} is unreadable: {e}") from e
            staged[base] = (base, info, md5, size)
    if not staged:
        raise DataError("the historical ZIP has no CSV files")
    return zip_path, [staged[k] for k in sorted(staged)]


def ingest(store, force=False, historical=False, resolve=resolve_resources,
           download=http_download, now=None):
    """Toronto Open Data -> raw zone. Returns the new recent blob path, or
    None when no recent file was uploaded.

    Downloads the recent CSV only when CKAN's last_modified is newer than the
    newest blob's source_last_modified, or with force. With force, skips the
    upload when the content matches the newest blob. Downloads the historical
    ZIP only when there's no complete historical folder, or with historical.
    Every file is validated before anything is uploaded. Historical files go
    up first and _SUCCESS last, then the recent file, then prune_recent.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    resources = resolve()
    source = resources["recent"]["last_modified"]
    newest = newest_recent(store)
    newest_source = newest[1].metadata.get(SOURCE_MODIFIED_KEY, "") if newest else ""
    need_recent = force or newest is None or source > newest_source
    need_historical = historical or newest_historical(store) is None
    if not need_recent and not need_historical:
        print(f"No new data: Toronto Open Data last modified {source}, already in {newest[0]}.")
        return None

    with tempfile.TemporaryDirectory() as tmp:
        zip_path, staged_historical = None, []
        if need_historical:
            zip_path, staged_historical = _download_historical(
                resources["historical"]["url"], tmp, download
            )
        recent_path = None
        if need_recent:
            recent_path = os.path.join(tmp, RECENT_NAME)
            print(f"Downloading {resources['recent']['url']} ...")
            download(resources["recent"]["url"], recent_path)
            rows = validate_csv(recent_path, RECENT_COLUMN_MAP, MIN_RECENT_ROWS)
            recent_md5 = md5_b64(recent_path)
            if newest and newest[1].md5 == recent_md5:
                print(f"Recent file unchanged since {newest[0]}; not uploading it.")
                os.remove(recent_path)  # free the tmpfs during the historical upload
                recent_path = None
            else:
                print(f"  {RECENT_NAME}: {rows} rows, valid")

        if staged_historical:
            with zipfile.ZipFile(zip_path) as zf:
                for name, info, md5, size in staged_historical:
                    try:
                        with zf.open(info) as body:
                            store.upload(f"{HISTORICAL_PREFIX}{stamp}/{name}", body, md5, length=size)
                    except ZIP_MEMBER_ERRORS as e:
                        raise DataError(f"historical ZIP member {info.filename} is unreadable: {e}") from e
            os.remove(zip_path)
            store.upload(
                f"{HISTORICAL_PREFIX}{stamp}/{SUCCESS_MARKER}",
                io.BytesIO(b""),
                md5_b64(io.BytesIO(b"")),
                length=0,
            )
            print(f"Uploaded {len(staged_historical)} historical files to {HISTORICAL_PREFIX}{stamp}/")

        if recent_path is None:
            return None
        name = f"{RECENT_PREFIX}{stamp}/{RECENT_NAME}"
        store.upload(name, recent_path, recent_md5, metadata={SOURCE_MODIFIED_KEY: source})
        print(f"Uploaded {name}")
    prune_recent(store)
    return name


def prune_recent(store, keep=KEEP_RECENT):
    """Delete recent/ folders beyond the newest `keep`. Never deletes the newest."""
    if keep < 1:
        raise ValueError("keep must be at least 1")
    blobs = store.list(RECENT_PREFIX)
    old = folders(blobs, RECENT_PREFIX)[:-keep]
    for folder in old:
        for name in sorted(n for n in blobs if n.startswith(f"{RECENT_PREFIX}{folder}/")):
            store.delete(name)
    if old:
        print(f"Pruned {len(old)} old {RECENT_PREFIX} folders.")


# ---------------------------------------------------------------------------
# Staleness check
# ---------------------------------------------------------------------------

def check_fresh(store, now=None):
    """Raise DataError if the newest recent file's source is older than STALE_AFTER.

    Toronto Open Data publishes most business days, so a long gap usually
    means the dataset moved or its ID changed.
    """
    newest = require_newest_recent(store)
    source = newest[1].metadata.get(SOURCE_MODIFIED_KEY)
    if not source:
        raise DataError(f"{newest[0]} has no {SOURCE_MODIFIED_KEY} metadata")
    when = datetime.datetime.fromisoformat(source)
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if now - when > STALE_AFTER:
        raise DataError(
            f"the newest data is from {source}, more than {STALE_AFTER.days} days old. "
            "Check that Toronto Open Data still publishes the DineSafe dataset."
        )
