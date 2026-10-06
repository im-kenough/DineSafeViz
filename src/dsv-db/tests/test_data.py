import base64
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile as _zipfile
from email.message import Message
from urllib.error import HTTPError

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data import BlobStore, DataError, md5_b64, validate_csv
from refresh import HISTORICAL_COLUMN_MAP, RECENT_COLUMN_MAP

RECENT_HEADER = ",".join(["_id", "phone", "observation", *RECENT_COLUMN_MAP])
HIST_HEADER = ",".join(['"Rec #"', *(f'"{c}"' for c in HISTORICAL_COLUMN_MAP)])


def write_csv(path, header, rows, encoding="utf-8"):
    width = header.count(",") + 1
    lines = [header] + [",".join(["x"] * width) for _ in range(rows)]
    path.write_bytes(("\n".join(lines) + "\n").encode(encoding))
    return path


def b64md5(data):
    return base64.b64encode(hashlib.md5(data).digest()).decode()


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
    """Records requests; answers from a dict of {(method, blob): FakeResponse | int}."""

    def __init__(self, answers):
        self.answers = answers
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        blob = req.full_url.split("/dinesafe/", 1)[1]
        answer = self.answers.get((req.get_method(), blob), 404)
        if isinstance(answer, int):
            raise HTTPError(req.full_url, answer, "error", Message(), io.BytesIO(b""))
        return answer


class TestMd5:
    def test_is_base64_digest(self, tmp_path):
        p = tmp_path / "f"
        p.write_bytes(b"hello")
        assert md5_b64(str(p)) == b64md5(b"hello")


class TestValidateCsv:
    def test_valid_recent_returns_row_count(self, tmp_path):
        p = write_csv(tmp_path / "r.csv", RECENT_HEADER, 3)
        assert validate_csv(str(p), RECENT_COLUMN_MAP, min_rows=3) == 3

    def test_valid_cp1252_historical(self, tmp_path):
        p = write_csv(tmp_path / "h.csv", HIST_HEADER + ",caf\xe9", 2, "cp1252")
        assert validate_csv(str(p), HISTORICAL_COLUMN_MAP, min_rows=1) == 2

    def test_missing_column_names_it(self, tmp_path):
        header = RECENT_HEADER.replace("severity", "sev")
        p = write_csv(tmp_path / "r.csv", header, 3)
        with pytest.raises(DataError, match="severity"):
            validate_csv(str(p), RECENT_COLUMN_MAP, min_rows=1)

    def test_too_few_rows(self, tmp_path):
        p = write_csv(tmp_path / "r.csv", RECENT_HEADER, 2)
        with pytest.raises(DataError, match="2 rows"):
            validate_csv(str(p), RECENT_COLUMN_MAP, min_rows=3)


class TestBlobStore:
    def test_requests_carry_bearer_token_and_version(self):
        opener = FakeOpener({("HEAD", "Dinesafe.csv"): FakeResponse(headers={"Content-MD5": "abc="})})
        store = BlobStore("stdsvstg01", "dinesafe", "tok", opener=opener)
        assert store.get_md5("Dinesafe.csv") == "abc="
        req = opener.requests[0]
        assert req.full_url == "https://stdsvstg01.blob.core.windows.net/dinesafe/Dinesafe.csv"
        assert req.get_header("Authorization") == "Bearer tok"
        assert req.get_header("X-ms-version") == "2023-11-03"

    def test_get_md5_of_missing_blob_is_none(self):
        store = BlobStore("a", "dinesafe", "t", opener=FakeOpener({}))
        assert store.get_md5("nope.csv") is None

    def test_other_http_errors_raise_data_error(self):
        opener = FakeOpener({("HEAD", "x.csv"): 403})
        store = BlobStore("a", "dinesafe", "t", opener=opener)
        with pytest.raises(DataError, match="403"):
            store.get_md5("x.csv")

    def test_upload_sends_block_blob_with_md5(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_bytes(b"data")
        opener = FakeOpener({("PUT", "dinesafe-historical/f.csv"): FakeResponse(status=201)})
        store = BlobStore("a", "dinesafe", "t", opener=opener)
        store.upload("dinesafe-historical/f.csv", str(p), b64md5(b"data"))
        req = opener.requests[0]
        assert req.get_method() == "PUT"
        assert req.get_header("X-ms-blob-type") == "BlockBlob"
        assert req.get_header("Content-md5") == b64md5(b"data")
        assert req.data == b"data"

    def test_download_to_writes_file(self, tmp_path):
        opener = FakeOpener({("GET", "Dinesafe.csv"): FakeResponse(b"csv")})
        store = BlobStore("a", "dinesafe", "t", opener=opener)
        store.download_to("Dinesafe.csv", str(tmp_path / "out"))
        assert (tmp_path / "out").read_bytes() == b"csv"

    def test_read_manifest_missing_is_none(self):
        assert BlobStore("a", "dinesafe", "t", opener=FakeOpener({})).read_manifest() is None

    def test_read_manifest_parses_json(self):
        body = json.dumps({"files": []}).encode()
        opener = FakeOpener({("GET", "manifest.json"): FakeResponse(body)})
        assert BlobStore("a", "dinesafe", "t", opener=opener).read_manifest() == {"files": []}
