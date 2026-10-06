"""Fixtures for the repo-level tests. Helpers live in helpers.py."""
import os
import shutil

import pytest

from helpers import FAKES, ROOT, SECRETS


@pytest.fixture
def vm_repo(tmp_path):
    """A copy of scripts/ and deploy/ (examples copied to the real names), with fake curl, git, and docker on PATH.

    Returns (repo_dir, env, log_path). Each fake appends its command line to
    the log, so tests can check what ran and in what order.
    """
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", repo / "scripts")
    shutil.copytree(ROOT / "deploy", repo / "deploy")
    # The real settings files are gitignored; the operator copies them from
    # the committed examples, as the VM setup guide says.
    for example in (repo / "deploy").glob("*.env-example"):
        shutil.copy(example, example.with_suffix(".env"))
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    for name, value in SECRETS.items():
        (secrets_dir / name).write_text(value)
    log = tmp_path / "calls.log"
    log.touch()
    env = {
        "PATH": f"{FAKES}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "FAKE_LOG": str(log),
        "FAKE_SECRETS_DIR": str(secrets_dir),
    }
    return repo, env, log
