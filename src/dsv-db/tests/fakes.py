"""Fakes and CSV builders shared by the dsv-db tests."""
import base64
import csv
import hashlib
import io
import os
import sys
from email.message import Message
from urllib.error import HTTPError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data import BlobInfo, DataError
from refresh import HISTORICAL_COLUMN_MAP, RECENT_COLUMN_MAP

RECENT_FIELDS = ["_id", "phone", "observation", *RECENT_COLUMN_MAP]
HISTORICAL_FIELDS = ["Rec #", *HISTORICAL_COLUMN_MAP]
RECENT_HEADER = ",".join(RECENT_FIELDS)
HIST_HEADER = ",".join(f'"{c}"' for c in HISTORICAL_FIELDS)


def b64md5(data):
    return base64.b64encode(hashlib.md5(data).digest()).decode()


def write_csv(path, header, rows, encoding="utf-8"):
    """A CSV with the given header and `rows` rows of "x" (for validate_csv)."""
    width = header.count(",") + 1
    lines = [header] + [",".join(["x"] * width) for _ in range(rows)]
    path.write_bytes(("\n".join(lines) + "\n").encode(encoding))
    return path


def _write_dicts(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def recent_row(est_id, date, **extra):
    return {"estId": est_id, "estName": f"Place {est_id}",
            "address": "1 Main St M5V 1A1", "inspectionDate": date,
            "latitude": "43.6", "longitude": "-79.4", **extra}


def historical_row(est_id, date):
    return {"Establishment ID": est_id, "Establishment Name": f"Place {est_id}",
            "Establishment Address": "1 Main St", "Inspection Date": date,
            "Latitude": "43.6", "Longitude": "-79.4"}


def recent_csv(path, rows):
    return _write_dicts(path, RECENT_FIELDS, rows)


def historical_csv(path, rows):
    return _write_dicts(path, HISTORICAL_FIELDS, rows)


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", headers=None, status=200):
        super().__init__(body)
        self.status = status
        self.headers = Message()
        for k, v in (headers or {}).items():
            self.headers[k] = v

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """Records requests. Answers from {(method, suffix): FakeResponse | int},
    where suffix is the URL after the container URL, for example
    "/recent/x/Dinesafe.csv" or "?restype=container&comp=list&...".
    Unknown requests get 404."""

    CONTAINER = "https://a.blob.core.windows.net/dinesafe"

    def __init__(self, answers):
        self.answers = answers
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        suffix = req.full_url[len(self.CONTAINER):]
        answer = self.answers.get((req.get_method(), suffix), 404)
        if isinstance(answer, int):
            raise HTTPError(req.full_url, answer, "error", Message(), io.BytesIO(b""))
        return answer


class FakeStore:
    """In-memory raw zone with BlobStore's interface. Refuses overwrites,
    because the raw zone is append-only."""

    def __init__(self):
        self.blobs = {}  # {name: (bytes, metadata)}
        self.uploads = []
        self.deleted = []

    def put(self, name, data, **metadata):
        self.blobs[name] = (data, dict(metadata))

    def list(self, prefix):
        return {n: BlobInfo(dict(m), b64md5(b))
                for n, (b, m) in self.blobs.items() if n.startswith(prefix)}

    def download_to(self, name, path):
        if name not in self.blobs:
            raise DataError(f"{name} isn't in the container")
        with open(path, "wb") as f:
            f.write(self.blobs[name][0])

    def upload(self, name, path, md5, metadata=None):
        assert name not in self.blobs, f"overwrote {name}"
        with open(path, "rb") as f:
            body = f.read()
        assert b64md5(body) == md5, f"wrong MD5 for {name}"
        self.blobs[name] = (body, dict(metadata or {}))
        self.uploads.append(name)

    def delete(self, name):
        del self.blobs[name]
        self.deleted.append(name)
