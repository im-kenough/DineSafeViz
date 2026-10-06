"""init.sql and set-passwords.sh in the real Postgres image."""
import os
import subprocess
import time
import uuid

import pytest

from helpers import ROOT

IMAGE = "postgres:17.10"  # keep in sync with docker-compose.yml
SET_PASSWORDS = ROOT / "src" / "dsv-db" / "set-passwords.sh"
# A quote and a dollar sign prove the psql quoting in set-passwords.sh.
APP_PW = "app'pw$x"
MIGRATOR_PW = "migrator-pw"


def docker(*args, check=True):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=120
    )


def start_db(env):
    name = f"dsv-dbtest-{uuid.uuid4().hex[:8]}"
    args = [
        "run", "-d", "--name", name,
        "-e", "POSTGRES_USER=test_superuser",
        "-e", "POSTGRES_PASSWORD=superpw",
        "-e", "POSTGRES_DB=dinesafe",
        # --mount fails on a missing source; -v would create a root-owned dir.
        "--mount", f"type=bind,src={ROOT}/src/dsv-db/init.sql,dst=/docker-entrypoint-initdb.d/init.sql,readonly",
        "--mount", f"type=bind,src={SET_PASSWORDS},dst=/docker-entrypoint-initdb.d/set-passwords.sh,readonly",
    ]
    for key, value in env.items():
        args += ["-e", f"{key}={value}"]
    docker(*args, IMAGE)
    return name


def wait_ready(name, timeout=90):
    """True once Postgres accepts TCP connections, False if it exits.

    During init the image's temporary server listens on the Unix socket
    only, so a TCP answer means every init script has finished.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = docker("inspect", "-f", "{{.State.Status}}", name).stdout.strip()
        if state != "running":
            return False
        ready = docker(
            "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "test_superuser",
            check=False,
        )
        if ready.returncode == 0:
            return True
        time.sleep(1)
    raise TimeoutError(f"{name} didn't become ready in {timeout}s")


def login(name, user, password, sql="SELECT 1"):
    """Connect over TCP to the container's own address, which uses password auth."""
    ip = docker(
        "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name
    ).stdout.strip()
    return docker(
        "exec", "-e", f"PGPASSWORD={password}", name,
        "psql", "-h", ip, "-U", user, "-d", "dinesafe", "-tAc", sql,
        check=False,
    )


@pytest.fixture
def db():
    names = []

    def _start(env):
        name = start_db(env)
        names.append(name)
        return name

    yield _start
    for name in names:
        docker("rm", "-f", name, check=False)


@pytest.fixture(scope="module")
def ready_db():
    name = start_db(
        {"DSV_DB_APP_PASSWORD": APP_PW, "DSV_DB_MIGRATOR_PASSWORD": MIGRATOR_PW}
    )
    try:
        assert wait_ready(name), docker("logs", name).stderr
        yield name
    finally:
        docker("rm", "-f", name, check=False)


def test_set_passwords_is_executable():
    # The Postgres entrypoint sources non-executable .sh files, which would
    # leak this script's `set -u` into the entrypoint.
    assert os.access(SET_PASSWORDS, os.X_OK)


def test_roles_get_passwords_from_environment(ready_db):
    assert login(ready_db, "dinesafe_app", APP_PW).returncode == 0
    assert login(ready_db, "dinesafe_migrator", MIGRATOR_PW).returncode == 0


def test_old_hardcoded_passwords_no_longer_work(ready_db):
    assert login(ready_db, "dinesafe_app", "dinesafe_app").returncode != 0
    assert login(ready_db, "dinesafe_migrator", "dinesafe_migrator").returncode != 0


def test_app_role_has_statement_timeout(ready_db):
    result = login(ready_db, "dinesafe_app", APP_PW, "SHOW statement_timeout")
    assert result.stdout.strip() == "10s"


def test_app_role_is_still_read_only(ready_db):
    result = login(
        ready_db, "dinesafe_app", APP_PW,
        "INSERT INTO inspections (establishment_name) VALUES ('x')",
    )
    assert result.returncode != 0
    assert "permission denied" in result.stderr


@pytest.mark.parametrize("missing", ["DSV_DB_APP_PASSWORD", "DSV_DB_MIGRATOR_PASSWORD"])
def test_init_fails_when_a_password_is_unset(db, missing):
    env = {"DSV_DB_APP_PASSWORD": APP_PW, "DSV_DB_MIGRATOR_PASSWORD": MIGRATOR_PW}
    del env[missing]
    name = db(env)
    assert wait_ready(name) is False
    logs = docker("logs", name)
    assert missing in logs.stdout + logs.stderr
