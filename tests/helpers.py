"""Paths and helpers shared by the repo-level tests.

These tests cover the Azure VM deployment files: the deploy scripts, the
Compose override, the nginx config, and the database init scripts. App and
data-loader unit tests stay in src/dsv-app/tests and src/dsv-db/tests.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAKES = Path(__file__).resolve().parent / "fakes"

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
