"""The vendored Leaflet files match the checksums in SOURCE.md and are served."""
import hashlib
import re
from pathlib import Path

import pytest

import app as app_module

VENDOR = Path(app_module.app.static_folder) / "vendor" / "leaflet"
SERVED = ("leaflet.js", "leaflet.css")


def test_vendored_files_match_source_checksums():
    source = (VENDOR / "SOURCE.md").read_text()
    sums = re.findall(r"^([0-9a-f]{64})  (\S+)$", source, re.M)
    assert {name for _, name in sums} == {*SERVED, "LICENSE"}
    for digest, name in sums:
        assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == digest, name


@pytest.mark.parametrize("name", SERVED)
def test_vendored_files_are_served(client, name):
    resp = client.get(f"/static/vendor/leaflet/{name}")
    assert resp.status_code == 200
    assert resp.data == (VENDOR / name).read_bytes()
