"""Static checks of the merged Compose config (docker compose config)."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from helpers import ROOT

COMPOSE_DIR = Path(__file__).resolve().parent / "compose"


def compose_config(env_file, *files):
    cmd = ["docker", "compose", "--project-directory", str(ROOT), "--env-file", str(env_file)]
    for name in files:
        cmd += ["-f", str(ROOT / name)]
    cmd += ["config", "--format", "json"]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]},
    )


def load(env_file, *files):
    result = compose_config(env_file, *files)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def local():
    return load(COMPOSE_DIR / "local.env-test", "docker-compose.yml")


def test_local_db_role_passwords_default_to_todays_values(local):
    env = local["services"]["dsv-db"]["environment"]
    assert env["DSV_DB_APP_PASSWORD"] == "dinesafe_app"
    assert env["DSV_DB_MIGRATOR_PASSWORD"] == "dinesafe_migrator"


def test_local_db_runs_set_passwords_after_init_sql(local):
    targets = sorted(
        v["target"]
        for v in local["services"]["dsv-db"]["volumes"]
        if v["target"].startswith("/docker-entrypoint-initdb.d/")
    )
    # The image runs these in name order: init.sql creates the roles first.
    assert targets == [
        "/docker-entrypoint-initdb.d/init.sql",
        "/docker-entrypoint-initdb.d/set-passwords.sh",
    ]
