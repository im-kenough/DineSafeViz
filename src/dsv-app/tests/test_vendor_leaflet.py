"""The vendored Leaflet files match the checksums in SOURCE.md and are served."""
import hashlib
import re
from pathlib import Path

import pytest

import app as app_module

VENDOR = Path(app_module.app.static_folder) / "vendor" / "leaflet"


def test_vendored_files_match_source_checksums():
    source = (VENDOR / "SOURCE.md").read_text()
    sums = re.findall(r"^([0-9a-f]{64})  (\S+)$", source, re.M)
    assert {name for _, name in sums} == {"leaflet.js", "leaflet.css", "LICENSE"}
    for digest, name in sums:
        assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == digest, name


def test_source_names_the_pinned_version():
    source = (VENDOR / "SOURCE.md").read_text()
    assert "https://registry.npmjs.org/leaflet/-/leaflet-1.9.4.tgz" in source
    assert "sha512-nxS1ynzJOmOlHp+iL3FyWqK89GtNL8U8rvlMOsQdTTssxZwCXh8N2NB3GDQOL+YR3XnWyZAxwQixURb+FA74PA==" in source


@pytest.mark.parametrize("name", ["leaflet.js", "leaflet.css"])
def test_vendored_files_are_served(client, name):
    resp = client.get(f"/static/vendor/leaflet/{name}")
    assert resp.status_code == 200
    assert resp.data == (VENDOR / name).read_bytes()
