"""init.sql, the migrations, and set-passwords.sh in the real Postgres image."""
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from db_helpers import DB_DIR, docker, migrate, migrated_db, psql, run_migration, start_db, wait_ready

SET_PASSWORDS = DB_DIR / "set-passwords.sh"
# A quote and a dollar sign prove the psql quoting in set-passwords.sh.
APP_PW = "app'pw$x"
MIGRATOR_PW = "migrator-pw"


def login(name, user, password, sql="SELECT 1"):
    return psql(name, sql, user=user, password=password)


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
    with migrated_db({"DSV_DB_APP_PASSWORD": APP_PW, "DSV_DB_MIGRATOR_PASSWORD": MIGRATOR_PW}) as name:
        yield name


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


# The image's init runs init.sql and set-passwords.sh only. Migrations come
# from apply_migrations in scripts/lib.sh, which deploy.sh and every
# pipeline.sh load run first.
def test_new_volume_waits_for_a_migration(db):
    name = db({"DSV_DB_APP_PASSWORD": APP_PW, "DSV_DB_MIGRATOR_PASSWORD": MIGRATOR_PW})
    assert wait_ready(name), docker("logs", name).stderr
    assert "load_log" in psql(name, "SELECT count(*) FROM load_log").stderr
    assert migrate(name).returncode == 0
    result = login(name, "dinesafe_migrator", MIGRATOR_PW, "SELECT count(*) FROM load_log")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0"


def test_migration_runs_again_without_errors(ready_db):
    for _ in range(2):
        result = migrate(ready_db)
        assert result.returncode == 0, result.stderr


# Each file is one transaction: a failure part-way leaves no REVOKE without
# its GRANT, so a load running alongside sees the old grants or the new ones.
def test_failed_migration_rolls_back_the_whole_file(ready_db):
    result = run_migration(
        ready_db, "REVOKE ALL ON TABLE load_log FROM dinesafe_migrator; SELECT 1/0;"
    )
    assert result.returncode != 0
    result = login(ready_db, "dinesafe_migrator", MIGRATOR_PW, "SELECT count(*) FROM load_log")
    assert result.returncode == 0, result.stderr


# A deploy and the pipeline timer can migrate at once. Without a lock, two
# concurrent GRANTs on one table fail with "tuple concurrently updated".
def test_concurrent_migrations_all_succeed(ready_db):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: migrate(ready_db), range(12)))
    assert [r.stderr for r in results if r.returncode != 0] == []


def test_migrator_can_load(ready_db):
    sql = (
        "BEGIN;"
        "INSERT INTO inspections (establishment_name) VALUES ('x');"
        "DELETE FROM inspections WHERE establishment_name = 'x';"
        "INSERT INTO load_log (kind, recent_path, rows_deleted, rows_inserted)"
        " VALUES ('seed', 'recent/t/Dinesafe.csv', 0, 1);"
        "ROLLBACK;"
    )
    result = login(ready_db, "dinesafe_migrator", MIGRATOR_PW, sql)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("sql", [
    "CREATE TABLE sneaky (id int)",
    "TRUNCATE inspections",
    "DROP TABLE load_log",
    "UPDATE inspections SET severity = 'x'",
])
def test_migrator_can_do_nothing_else(ready_db, sql):
    result = login(ready_db, "dinesafe_migrator", MIGRATOR_PW, sql)
    assert result.returncode != 0
    assert "permission denied" in result.stderr or "must be owner" in result.stderr


def test_app_can_read_load_log_but_not_write(ready_db):
    assert login(ready_db, "dinesafe_app", APP_PW, "SELECT count(*) FROM load_log").returncode == 0
    result = login(ready_db, "dinesafe_app", APP_PW, "DELETE FROM load_log")
    assert "permission denied" in result.stderr
