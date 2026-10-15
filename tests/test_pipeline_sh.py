"""scripts/pipeline.sh with fake curl, az, and docker (tests/fakes)."""
import pytest

from helpers import run


def pipeline_sh(repo, env, *args):
    return run([repo / "scripts" / "pipeline.sh", *args], env, cwd=repo)


def calls(log):
    return log.read_text().splitlines()


def docker_calls(log):
    return [line for line in calls(log) if line.startswith("docker ")]


MIGRATE = "docker compose exec -T dsv-db sh -c psql -q -v ON_ERROR_STOP=1"
RUN = "docker compose --profile pipeline run --rm "


def run_calls(log):
    return [line for line in calls(log) if line.startswith(RUN)]


@pytest.mark.parametrize("args", [
    (), ("stg",), ("local", "load"), ("stg", "fetch"), ("stg", "load", "--historical"),
    ("dev", "run"), ("dev", "ingest"), ("stg", "run", "--bogus"),
])
def test_rejects_bad_arguments(vm_repo, args):
    repo, env, log = vm_repo
    assert pipeline_sh(repo, env, *args).returncode == 2
    assert docker_calls(log) == []


@pytest.mark.parametrize("command", ["run", "ingest", "load"])
def test_vm_runs_the_subcommand_with_a_storage_token(vm_repo, command):
    repo, env, log = vm_repo
    result = pipeline_sh(repo, env, "stg", command)
    assert result.returncode == 0, result.stderr
    imds = next(line for line in calls(log) if "169.254.169.254" in line)
    assert "resource=https%3A%2F%2Fstorage.azure.com%2F" in imds
    runs = run_calls(log)
    assert len(runs) == 1
    line = runs[0]
    assert line.endswith(f"dsv-pipeline {command}")
    assert "-e DSV_STORAGE_ACCOUNT=stdsvstg01" in line
    assert ":/run/secrets/storage-token:ro" in line
    assert "fake-token" not in line  # passed as a file, never on the command line
    assert "--build" not in line  # the VMs run the pulled image


def test_flags_are_passed_through(vm_repo):
    repo, env, log = vm_repo
    assert pipeline_sh(repo, env, "prod", "run", "--force", "--historical").returncode == 0
    line = run_calls(log)[0]
    assert line.endswith("dsv-pipeline run --force --historical")
    assert "stdsvprod01" in line


# Review focus 4: under cap_drop ALL, root can't read the operator's mode-600 token.
def test_runs_as_calling_user(vm_repo):
    repo, env, log = vm_repo
    assert pipeline_sh(repo, env, "stg", "load").returncode == 0
    assert "--user 1234:5678" in run_calls(log)[0]


def test_token_file_is_removed_afterwards(vm_repo, tmp_path):
    repo, env, log = vm_repo
    env = {**env, "TMPDIR": str(tmp_path / "tmp")}
    (tmp_path / "tmp").mkdir()
    assert pipeline_sh(repo, env, "stg", "run").returncode == 0
    assert list((tmp_path / "tmp").iterdir()) == []


def test_pipeline_failure_is_exit_1_and_still_removes_the_token(vm_repo, tmp_path):
    repo, env, log = vm_repo
    env = {**env, "TMPDIR": str(tmp_path / "tmp"), "FAKE_PIPELINE_EXIT": "1"}
    (tmp_path / "tmp").mkdir()
    assert pipeline_sh(repo, env, "stg", "run").returncode == 1
    assert list((tmp_path / "tmp").iterdir()) == []


def test_imds_failure_runs_nothing(vm_repo):
    repo, env, log = vm_repo
    result = pipeline_sh(repo, {**env, "FAKE_IMDS_DOWN": "1"}, "stg", "run")
    assert result.returncode == 1
    assert "IMDS" in result.stderr
    assert docker_calls(log) == []


def test_dev_loads_with_az_token_and_builds(vm_repo):
    repo, env, log = vm_repo
    result = pipeline_sh(repo, env, "dev", "load", "--force")
    assert result.returncode == 0, result.stderr
    assert any(line.startswith("az account get-access-token --resource https://storage.azure.com/")
               for line in calls(log))
    line = run_calls(log)[0]
    assert "--build" in line  # dev runs the working tree
    assert line.endswith("dsv-pipeline load --force")
    assert "stdsvstg01" in line


def test_dev_without_az_login_explains(vm_repo):
    repo, env, log = vm_repo
    result = pipeline_sh(repo, {**env, "FAKE_AZ_LOGGED_OUT": "1"}, "dev", "load")
    assert result.returncode == 1
    assert "az login" in result.stderr


def test_dev_without_settings_file_names_the_example(vm_repo):
    repo, env, log = vm_repo
    (repo / "deploy" / "dev.env").unlink()
    result = pipeline_sh(repo, env, "dev", "load")
    assert result.returncode == 1
    assert "deploy/dev.env-example" in result.stderr
    assert calls(log) == []


def test_invalid_account_name_is_rejected(vm_repo):
    repo, env, log = vm_repo
    with open(repo / "deploy" / "stg.env", "a") as f:
        f.write("DSV_STORAGE_ACCOUNT=Not_Valid\n")
    result = pipeline_sh(repo, env, "stg", "load")
    assert result.returncode == 1
    assert "isn't a valid storage account name" in result.stderr


# A fresh volume has no load_log and no grants for dinesafe_migrator until the
# migrations run, so every load applies them first, not only deploy.sh.
@pytest.mark.parametrize("env_name, command", [("stg", "load"), ("stg", "run"), ("dev", "load")])
def test_loads_apply_every_migration_first(vm_repo, env_name, command):
    repo, env, log = vm_repo
    assert pipeline_sh(repo, env, env_name, command).returncode == 0
    lines = calls(log)
    migrations = sorted((repo / "src" / "dsv-db" / "migrations").glob("*.sql"))
    # The command line itself is exercised against real Postgres in test_db_init.py.
    assert len([line for line in lines if line.startswith(MIGRATE)]) == len(migrations)
    assert max(i for i, line in enumerate(lines) if line.startswith(MIGRATE)) \
        < next(i for i, line in enumerate(lines) if line.startswith(RUN))


def test_ingest_never_touches_the_database(vm_repo):
    repo, env, log = vm_repo
    assert pipeline_sh(repo, env, "stg", "ingest").returncode == 0
    assert not [line for line in calls(log) if line.startswith(MIGRATE)]


def test_failed_migration_stops_before_the_load(vm_repo):
    repo, env, log = vm_repo
    result = pipeline_sh(repo, {**env, "FAKE_MIGRATE_EXIT": "1"}, "stg", "load")
    assert result.returncode == 1
    assert "migrations" in result.stderr
    assert run_calls(log) == []
