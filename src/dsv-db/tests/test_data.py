import base64
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile as _zipfile
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data import (
    MIN_HISTORICAL_ROWS,
    MIN_RECENT_ROWS,
    BlobStore,
    DataError,
    fetch,
    http_download,
    main,
    md5_b64,
    sync,
    validate_csv,
)
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
        opener = FakeOpener({("HEAD", "Dinesafe.csv"): FakeResponse(
            headers={"Content-MD5": "abc=", "x-ms-version-id": "2026-10-06T00:00:00.0000000Z"})})
        store = BlobStore("stdsvstg01", "dinesafe", "tok", opener=opener)
        assert store.stat("Dinesafe.csv") == ("abc=", "2026-10-06T00:00:00.0000000Z")
        req = opener.requests[0]
        assert req.full_url == "https://stdsvstg01.blob.core.windows.net/dinesafe/Dinesafe.csv"
        assert req.get_header("Authorization") == "Bearer tok"
        assert req.get_header("X-ms-version") == "2023-11-03"

    def test_stat_of_missing_blob_is_none(self):
        store = BlobStore("a", "dinesafe", "t", opener=FakeOpener({}))
        assert store.stat("nope.csv") is None

    def test_other_http_errors_raise_data_error(self):
        opener = FakeOpener({("HEAD", "x.csv"): 403})
        store = BlobStore("a", "dinesafe", "t", opener=opener)
        with pytest.raises(DataError, match="403"):
            store.stat("x.csv")

    def test_upload_sends_block_blob_with_md5(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_bytes(b"data")
        opener = FakeOpener({("PUT", "dinesafe-historical/f.csv"): FakeResponse(
            status=201, headers={"x-ms-version-id": "v1"})})
        store = BlobStore("a", "dinesafe", "t", opener=opener)
        assert store.upload("dinesafe-historical/f.csv", str(p), b64md5(b"data")) == "v1"
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

    def test_download_to_a_pinned_version(self, tmp_path):
        opener = FakeOpener({("GET", "Dinesafe.csv?versionid=2026-10-06T00%3A00%3A00Z"): FakeResponse(b"old")})
        store = BlobStore("a", "dinesafe", "t", opener=opener)
        store.download_to("Dinesafe.csv", str(tmp_path / "out"), "2026-10-06T00:00:00Z")
        assert (tmp_path / "out").read_bytes() == b"old"

    def test_read_manifest_missing_is_none(self):
        assert BlobStore("a", "dinesafe", "t", opener=FakeOpener({})).read_manifest() is None

    def test_read_manifest_parses_json(self):
        body = json.dumps({"files": []}).encode()
        opener = FakeOpener({("GET", "manifest.json"): FakeResponse(body)})
        assert BlobStore("a", "dinesafe", "t", opener=opener).read_manifest() == {"files": []}


class FakeStore:
    """In-memory container. blobs: {name: bytes}. Records upload order."""

    def __init__(self, blobs=None):
        self.blobs = dict(blobs or {})
        self.uploads = []
        self.versions = {}  # {(name, version id): bytes}, like Blob versioning
        self.current = {}   # {name: current version id}

    def stat(self, name):
        if name not in self.blobs:
            return None
        return b64md5(self.blobs[name]), self.current.get(name)

    def download_to(self, name, path, version_id=None):
        data = self.versions.get((name, version_id)) if version_id else self.blobs.get(name)
        if data is None:
            raise DataError(f"{name} isn't in the container")
        with open(path, "wb") as f:
            f.write(data)

    def upload(self, name, path, md5):
        with open(path, "rb") as f:
            self.blobs[name] = f.read()
        version_id = f"v{len(self.versions) + 1}"
        self.versions[(name, version_id)] = self.blobs[name]
        self.current[name] = version_id
        self.uploads.append(name)
        return version_id

    def read_manifest(self):
        raw = self.blobs.get("manifest.json")
        return json.loads(raw) if raw else None

    def write_manifest(self, manifest, staging_dir):
        path = os.path.join(staging_dir, "manifest.json")
        with open(path, "w") as f:
            json.dump(manifest, f)
        self.upload("manifest.json", path, md5_b64(path))


def fake_download(tmp_path, recent_rows=MIN_RECENT_ROWS, recent_header=RECENT_HEADER):
    """A urlretrieve stand-in serving a recent CSV and a 2-file historical ZIP."""
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    recent = write_csv(src / "dinesafe.csv", recent_header, recent_rows)
    zpath = src / "hist.zip"
    with _zipfile.ZipFile(zpath, "w") as zf:
        for year in (2001, 2002):
            h = write_csv(src / f"dinesafe_hist_{year}.csv", HIST_HEADER, MIN_HISTORICAL_ROWS)
            zf.write(h, f"some folder/dinesafe_hist_{year}.csv")
        zf.writestr("readme.txt", "not a csv")

    def download(url, path):
        shutil.copy(recent if url.endswith("dinesafe.csv") else zpath, path)

    return download


class TestFetch:
    def test_first_fetch_uploads_everything_and_manifest_last(self, tmp_path):
        store = FakeStore()
        manifest = fetch(store, str(tmp_path / "data"), historical=False,
                         download=fake_download(tmp_path))
        names = {f["name"] for f in manifest["files"]}
        assert names == {"Dinesafe.csv", "dinesafe-historical/dinesafe_hist_2001.csv",
                         "dinesafe-historical/dinesafe_hist_2002.csv"}
        assert store.uploads[-1] == "manifest.json"
        assert len(store.uploads) == 4
        recent = next(f for f in manifest["files"] if f["name"] == "Dinesafe.csv")
        assert recent["rows"] == MIN_RECENT_ROWS
        assert recent["md5"] == b64md5(store.blobs["Dinesafe.csv"])

    def test_unchanged_files_are_not_reuploaded(self, tmp_path):
        store = FakeStore()
        dl = fake_download(tmp_path)
        fetch(store, str(tmp_path / "data"), historical=False, download=dl)
        store.uploads.clear()
        fetch(store, str(tmp_path / "data"), historical=False, download=dl)
        assert store.uploads == ["manifest.json"]

    def test_historical_is_carried_over_unless_requested(self, tmp_path):
        store = FakeStore()
        dl = fake_download(tmp_path)
        fetch(store, str(tmp_path / "data"), historical=False, download=dl)
        calls = []

        def counting(url, path):
            calls.append(url)
            dl(url, path)

        manifest = fetch(store, str(tmp_path / "data"), historical=False, download=counting)
        assert len(calls) == 1  # recent only
        assert len(manifest["files"]) == 3
        fetch(store, str(tmp_path / "data"), historical=True, download=counting)
        assert len(calls) == 3  # recent + ZIP

    def test_fetch_rejects_missing_column_and_uploads_nothing(self, tmp_path):
        store = FakeStore()
        bad = RECENT_HEADER.replace("estId", "establishmentId")
        with pytest.raises(DataError, match="estId"):
            fetch(store, str(tmp_path / "data"), historical=False,
                  download=fake_download(tmp_path, recent_header=bad))
        assert store.uploads == []

    def test_manifest_pins_each_file_version(self, tmp_path):
        store = FakeStore()
        manifest = fetch(store, str(tmp_path / "data"), historical=False,
                         download=fake_download(tmp_path))
        for entry in manifest["files"]:
            assert entry["version_id"] == store.current[entry["name"]]

    def test_bad_zip_is_a_data_error(self, tmp_path):
        good = fake_download(tmp_path)

        def download(url, path):
            good(url, path)
            if not url.endswith("dinesafe.csv"):
                with open(path, "wb") as f:
                    f.write(b"<html>maintenance</html>")

        with pytest.raises(DataError, match="ZIP"):
            fetch(FakeStore(), str(tmp_path / "data"), historical=False, download=download)

    def test_staging_is_cleaned_up(self, tmp_path):
        fetch(FakeStore(), str(tmp_path / "data"), historical=False,
              download=fake_download(tmp_path))
        assert not (tmp_path / "data" / ".staging").exists()


class TestSync:
    def seeded_store(self, tmp_path):
        store = FakeStore()
        fetch(store, str(tmp_path / "seed"), historical=False, download=fake_download(tmp_path))
        return store

    def test_sync_mirrors_manifest_files(self, tmp_path):
        store = self.seeded_store(tmp_path)
        data = tmp_path / "data"
        sync(store, str(data))
        assert (data / "manifest.json").exists()
        assert (data / "Dinesafe.csv").read_bytes() == store.blobs["Dinesafe.csv"]
        assert (data / "dinesafe-historical" / "dinesafe_hist_2001.csv").exists()

    def test_sync_skips_files_that_already_match(self, tmp_path):
        store = self.seeded_store(tmp_path)
        data = tmp_path / "data"
        sync(store, str(data))
        before = (data / "Dinesafe.csv").stat().st_mtime_ns
        sync(store, str(data))
        assert (data / "Dinesafe.csv").stat().st_mtime_ns == before

    def test_sync_md5_mismatch_keeps_old_file(self, tmp_path):
        store = self.seeded_store(tmp_path)
        data = tmp_path / "data"
        sync(store, str(data))
        old = (data / "Dinesafe.csv").read_bytes()
        manifest = json.loads(store.blobs["manifest.json"])
        for f in manifest["files"]:
            if f["name"] == "Dinesafe.csv":
                f["md5"] = b64md5(b"something else")
        store.blobs["manifest.json"] = json.dumps(manifest).encode()
        store.blobs["Dinesafe.csv"] = b"corrupted"
        with pytest.raises(DataError, match="Dinesafe.csv"):
            sync(store, str(data))
        assert (data / "Dinesafe.csv").read_bytes() == old
        assert not list(data.rglob("*.part"))

    def test_sync_removes_csvs_not_in_manifest(self, tmp_path):
        store = self.seeded_store(tmp_path)
        data = tmp_path / "data"
        sync(store, str(data))
        stale = data / "dinesafe-historical" / "dinesafe_hist_1999.csv"
        stale.write_text("old")
        sync(store, str(data))
        assert not stale.exists()

    def test_sync_after_partial_upload_gets_the_manifest_versions(self, tmp_path):
        store = self.seeded_store(tmp_path)
        old = store.blobs["Dinesafe.csv"]
        # A later fetch uploaded a new Dinesafe.csv, then failed before the manifest.
        p = tmp_path / "new.csv"
        p.write_bytes(old + b"x,y\n")
        store.upload("Dinesafe.csv", str(p), b64md5(p.read_bytes()))
        data = tmp_path / "fresh"
        sync(store, str(data))
        assert (data / "Dinesafe.csv").read_bytes() == old

    def test_sync_without_manifest_fails(self, tmp_path):
        with pytest.raises(DataError, match="manifest.json"):
            sync(FakeStore(), str(tmp_path / "data"))


class TestMain:
    def test_missing_account_is_a_clear_error(self, tmp_path, monkeypatch, capsys):
        token = tmp_path / "token"
        token.write_text("t")
        monkeypatch.delenv("DSV_STORAGE_ACCOUNT", raising=False)
        monkeypatch.setenv("DSV_TOKEN_FILE", str(token))
        assert main(["sync"]) == 1
        assert "DSV_STORAGE_ACCOUNT" in capsys.readouterr().err

    def test_missing_token_file_is_a_clear_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("DSV_STORAGE_ACCOUNT", "stdsvstg01")
        monkeypatch.setenv("DSV_TOKEN_FILE", str(tmp_path / "nope"))
        assert main(["sync"]) == 1
        assert "token" in capsys.readouterr().err


class TestHttpDownload:
    def test_passes_a_timeout_and_writes_the_body(self, tmp_path):
        seen = {}

        def opener(url, timeout=None):
            seen["timeout"] = timeout
            return FakeResponse(b"body")

        http_download("https://example.test/f.csv", str(tmp_path / "f"), opener=opener)
        assert (tmp_path / "f").read_bytes() == b"body"
        assert seen["timeout"] and seen["timeout"] <= 300

    @pytest.mark.parametrize("error", [
        URLError("timed out"),
        HTTPError("https://example.test/f.csv", 503, "Service Unavailable", Message(), io.BytesIO(b"")),
        TimeoutError("timed out"),
    ])
    def test_network_errors_are_data_errors(self, tmp_path, error):
        def opener(url, timeout=None):
            raise error

        with pytest.raises(DataError, match="example.test"):
            http_download("https://example.test/f.csv", str(tmp_path / "f"), opener=opener)
