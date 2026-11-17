"""Fixtures for the repo-level tests. Helpers live in helpers.py and db_helpers.py."""
import os
import shutil

import pytest

from helpers import FAKES, ROOT, SECRETS


@pytest.fixture
def fake_env(tmp_path):
    """An environment with the command fakes in tests/fakes first on PATH.

    Returns (env, log_path). Each fake appends its command line to the log,
    so tests can check what ran and in what order.
    """
    log = tmp_path / "calls.log"
    log.touch()
    env = {
        "PATH": f"{FAKES}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "FAKE_LOG": str(log),
    }
    return env, log


@pytest.fixture
def vm_repo(tmp_path, fake_env):
    """A copy of scripts/, deploy/ (examples copied to the real names) and the
    migrations, run with fake_env and a fake Key Vault holding SECRETS.

    Returns (repo_dir, env, log_path).
    """
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", repo / "scripts")
    shutil.copytree(ROOT / "deploy", repo / "deploy")
    shutil.copytree(ROOT / "src" / "dsv-db" / "migrations", repo / "src" / "dsv-db" / "migrations")
    # The real settings files are gitignored; the operator copies them from
    # the committed examples, as the VM setup guide says.
    for example in (repo / "deploy").glob("*.env-example"):
        shutil.copy(example, example.with_suffix(".env"))
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    for name, value in SECRETS.items():
        (secrets_dir / name).write_text(value)
    env, log = fake_env
    env["FAKE_SECRETS_DIR"] = str(secrets_dir)
    return repo, env, log


@pytest.fixture(scope="session")
def ready_db():
    """A started, ready, fully migrated Postgres container, shared by the DB
    tests in the run and removed at the end. Fixtures that add rows clear the
    tables first. Tests that change roles, grants or the schema use their own
    container instead (own_db in test_db_init.py)."""
    # Imported here so only DB tests need psycopg2 and db_helpers' file parsing.
    from db_helpers import migrated_db

    with migrated_db() as name:
        yield name
