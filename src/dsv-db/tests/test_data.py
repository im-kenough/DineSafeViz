import io
import json
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from fakes import (
    HIST_HEADER, RECENT_HEADER, FakeOpener, FakeResponse, FakeStore, b64md5, write_csv,
)
from data import (
    BlobStore, DataError, folders, http_download, md5_b64, newest_historical,
    newest_recent, resolve_resources, validate_csv,
)
from refresh import HISTORICAL_COLUMN_MAP, RECENT_COLUMN_MAP

LIST = "?restype=container&comp=list&prefix=recent%2F&include=metadata"


def listing(blobs, next_marker=""):
    """Blob service List Blobs XML for {name: (md5, {metadata})}."""
    items = "".join(
        f"<Blob><Name>{n}</Name><Properties><Content-MD5>{md5}</Content-MD5></Properties>"
        f"<Metadata>{''.join(f'<{k}>{v}</{k}>' for k, v in meta.items())}</Metadata></Blob>"
        for n, (md5, meta) in blobs.items()
    )
    return FakeResponse((
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<EnumerationResults ContainerName="dinesafe"><Blobs>{items}</Blobs>'
        f"<NextMarker>{next_marker}</NextMarker></EnumerationResults>"
    ).encode())


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
        p = write_csv(tmp_path / "r.csv", RECENT_HEADER.replace("severity", "sev"), 3)
        with pytest.raises(DataError, match="severity"):
            validate_csv(str(p), RECENT_COLUMN_MAP, min_rows=1)

    def test_too_few_rows(self, tmp_path):
        p = write_csv(tmp_path / "r.csv", RECENT_HEADER, 2)
        with pytest.raises(DataError, match="2 rows"):
            validate_csv(str(p), RECENT_COLUMN_MAP, min_rows=3)


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
        HTTPError("https://example.test/f.csv", 503, "Unavailable", Message(), io.BytesIO(b"")),
        TimeoutError("timed out"),
    ])
    def test_network_errors_are_data_errors(self, tmp_path, error):
        def opener(url, timeout=None):
            raise error

        with pytest.raises(DataError, match="example.test"):
            http_download("https://example.test/f.csv", str(tmp_path / "f"), opener=opener)


def package(*resources):
    return FakeResponse(json.dumps({"success": True, "result": {"resources": list(resources)}}).encode())


RECENT_RES = {"name": "Dinesafe.csv", "format": "CSV", "url": "https://t.test/recent.csv",
              "last_modified": "2026-10-11T08:18:39.697474"}
HIST_RES = {"name": "Dinesafe Historical Data", "format": "ZIP", "url": "https://t.test/hist.zip",
            "last_modified": "2026-07-06T13:07:17.168414"}
TM_RES = {"name": "Dinesafe™.csv", "format": "CSV", "url": "https://t.test/old.csv",
          "last_modified": "2026-07-08T21:00:32.773986"}


class TestResolveResources:
    def test_picks_recent_and_historical_by_name(self):
        found = resolve_resources(opener=lambda url, timeout=None: package(RECENT_RES, HIST_RES))
        assert found == {
            "recent": {"url": "https://t.test/recent.csv", "last_modified": "2026-10-11T08:18:39.697474"},
            "historical": {"url": "https://t.test/hist.zip", "last_modified": "2026-07-06T13:07:17.168414"},
        }

    # Review focus 2: the package still lists the old-schema Dinesafe™.csv.
    def test_ignores_the_trademark_variant(self):
        found = resolve_resources(opener=lambda url, timeout=None: package(TM_RES, RECENT_RES, HIST_RES))
        assert found["recent"]["url"] == "https://t.test/recent.csv"

    def test_missing_resource_names_it(self):
        with pytest.raises(DataError, match="Dinesafe Historical Data"):
            resolve_resources(opener=lambda url, timeout=None: package(RECENT_RES))

    def test_network_error_is_a_data_error(self):
        def opener(url, timeout=None):
            raise URLError("down")

        with pytest.raises(DataError, match="package_show"):
            resolve_resources(opener=opener)

    def test_non_json_is_a_data_error(self):
        with pytest.raises(DataError, match="JSON"):
            resolve_resources(opener=lambda url, timeout=None: FakeResponse(b"<html>"))


class TestBlobStore:
    def store(self, answers):
        opener = FakeOpener(answers)
        return BlobStore("a", "dinesafe", "tok", opener=opener), opener

    def test_requests_carry_bearer_token_and_version(self):
        store, opener = self.store({("GET", LIST): listing({})})
        store.list("recent/")
        req = opener.requests[0]
        assert req.get_header("Authorization") == "Bearer tok"
        assert req.get_header("X-ms-version") == "2023-11-03"

    def test_list_returns_metadata_and_md5(self):
        store, _ = self.store({("GET", LIST): listing({
            "recent/20261009T113005Z/Dinesafe.csv": ("abc=", {"source_last_modified": "2026-10-09T08:00:00"}),
        })})
        blobs = store.list("recent/")
        info = blobs["recent/20261009T113005Z/Dinesafe.csv"]
        assert info.md5 == "abc="
        assert info.metadata == {"source_last_modified": "2026-10-09T08:00:00"}

    def test_list_follows_next_marker(self):
        store, _ = self.store({
            ("GET", LIST): listing({"recent/a/Dinesafe.csv": ("1=", {})}, next_marker="m2"),
            ("GET", LIST + "&marker=m2"): listing({"recent/b/Dinesafe.csv": ("2=", {})}),
        })
        assert set(store.list("recent/")) == {"recent/a/Dinesafe.csv", "recent/b/Dinesafe.csv"}

    def test_list_of_missing_container_is_an_error(self):
        store, _ = self.store({})
        with pytest.raises(DataError, match="container"):
            store.list("recent/")

    def test_other_http_errors_raise_data_error(self):
        store, _ = self.store({("GET", LIST): 403})
        with pytest.raises(DataError, match="403"):
            store.list("recent/")

    def test_upload_sends_block_blob_md5_and_metadata(self, tmp_path):
        p = tmp_path / "f.csv"
        p.write_bytes(b"data")
        store, opener = self.store({("PUT", "/recent/t/Dinesafe.csv"): FakeResponse(status=201)})
        store.upload("recent/t/Dinesafe.csv", str(p), b64md5(b"data"),
                     metadata={"source_last_modified": "2026-10-11T08:18:39"})
        req = opener.requests[0]
        assert req.get_method() == "PUT"
        assert req.get_header("X-ms-blob-type") == "BlockBlob"
        assert req.get_header("Content-md5") == b64md5(b"data")
        assert req.get_header("X-ms-meta-source_last_modified") == "2026-10-11T08:18:39"
        assert req.data == b"data"

    def test_download_to_writes_file(self, tmp_path):
        store, _ = self.store({("GET", "/recent/t/Dinesafe.csv"): FakeResponse(b"csv")})
        store.download_to("recent/t/Dinesafe.csv", str(tmp_path / "out"))
        assert (tmp_path / "out").read_bytes() == b"csv"

    def test_download_of_missing_blob_is_an_error(self, tmp_path):
        store, _ = self.store({})
        with pytest.raises(DataError, match="isn't in the container"):
            store.download_to("recent/t/Dinesafe.csv", str(tmp_path / "out"))

    def test_delete_sends_delete(self):
        store, opener = self.store({("DELETE", "/recent/t/Dinesafe.csv"): FakeResponse(status=202)})
        store.delete("recent/t/Dinesafe.csv")
        assert opener.requests[0].get_method() == "DELETE"


class TestNewest:
    def test_folders_are_sorted_and_unique(self):
        names = ["recent/b/Dinesafe.csv", "recent/a/Dinesafe.csv", "recent/a/other", "recent/loose"]
        assert folders(names, "recent/") == ["a", "b"]

    def test_newest_recent_is_the_last_folder(self):
        store = FakeStore()
        store.put("recent/20261009T113005Z/Dinesafe.csv", b"old", source_last_modified="2026-10-09")
        store.put("recent/20261012T113012Z/Dinesafe.csv", b"new", source_last_modified="2026-10-12")
        path, info = newest_recent(store)
        assert path == "recent/20261012T113012Z/Dinesafe.csv"
        assert info.metadata["source_last_modified"] == "2026-10-12"

    def test_newest_recent_of_empty_zone_is_none(self):
        assert newest_recent(FakeStore()) is None

    def test_newest_historical_lists_its_csvs(self):
        store = FakeStore()
        for name in ("a.csv", "b.csv", "_SUCCESS"):
            store.put(f"historical/20261012T113012Z/{name}", b"x")
        folder, names = newest_historical(store)
        assert folder == "historical/20261012T113012Z/"
        assert names == ["historical/20261012T113012Z/a.csv", "historical/20261012T113012Z/b.csv"]

    # Review focus 1: an ingest that died partway leaves a folder without _SUCCESS.
    def test_newest_historical_ignores_folders_without_success(self):
        store = FakeStore()
        for name in ("a.csv", "_SUCCESS"):
            store.put(f"historical/20260601T113002Z/{name}", b"x")
        store.put("historical/20261012T113012Z/a.csv", b"partial")
        folder, _ = newest_historical(store)
        assert folder == "historical/20260601T113002Z/"

    def test_newest_historical_of_empty_zone_is_none(self):
        assert newest_historical(FakeStore()) is None
