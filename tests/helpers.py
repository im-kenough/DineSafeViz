"""Paths and helpers shared by the repo-level tests.

These tests cover the Azure VM deployment files: the deploy scripts, the
Compose override, the nginx config, and the database init scripts. App and
data-loader unit tests stay in src/dsv-app/tests and src/dsv-pipeline/tests.
"""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAKES = Path(__file__).resolve().parent / "fakes"


def compose_image(repo):
    """The image docker-compose.yml runs for repo (e.g. "nginx"), digest
    included, so tests follow Dependabot's bumps."""
    return re.search(rf"image: ({repo}:\S+)", (ROOT / "docker-compose.yml").read_text())[1]

# Values the fake Key Vault returns, keyed by secret name.
SECRETS = {
    "dsv-db-password": "super-secret-1",
    "dsv-db-migrator-password": "migrator-secret-2",
    "dsv-db-app-password": "app-secret-3",
    "dsv-analytics-admin-password": "grafana-secret-4",
    "dsv-tunnel-token": "eyJhIjoiZmFrZSJ9",
}


def run(cmd, env, cwd=None):
    """Run a command with an explicit environment and capture its output."""
    return subprocess.run(
        [str(c) for c in cmd],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )


def host_env():
    """The minimal environment the real docker CLI needs."""
    return {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]}


def docker(*args, check=True):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=120
    )


# The fakes in tests/fakes append each command line to a log; these read it.
MIGRATE = "docker compose exec -T dsv-db sh -c psql -q -v ON_ERROR_STOP=1"


def calls(log):
    return log.read_text().splitlines()


def first(lines, prefix):
    return next(i for i, line in enumerate(lines) if line.startswith(prefix))


def ran(lines, prefix):
    return any(line.startswith(prefix) for line in lines)
