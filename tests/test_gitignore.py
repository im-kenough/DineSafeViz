"""Real environment files stay out of git wherever they are; examples don't."""
import subprocess

import pytest

from helpers import ROOT


def ignored(path):
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path], cwd=ROOT
    )
    return result.returncode == 0


@pytest.mark.parametrize("path", [
    ".env",
    ".env.local",
    ".env.Ab12Cd",  # fetch-secrets.sh temp file
    "deploy/stg.env",
    "deploy/prod.env",
    "src/dsv-app/.env",
    "infra/some/dir/prod.env",
])
def test_real_env_files_are_ignored(path):
    assert ignored(path)


@pytest.mark.parametrize("path", [
    ".env.example",
    "deploy/stg.env-example",
    "deploy/prod.env-example",
    "tests/compose/local.env-test",
])
def test_examples_and_fixtures_are_not_ignored(path):
    assert not ignored(path)


@pytest.mark.parametrize("path", ["data/Dinesafe.csv", "data/manifest.json",
                                  "data/dinesafe-historical/dinesafe_hist_2001.csv"])
def test_synced_data_is_ignored(path):
    assert ignored(path)
