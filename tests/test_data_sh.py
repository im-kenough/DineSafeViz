"""scripts/data.sh with fake curl, az, and docker (tests/fakes)."""
import pytest

from helpers import run


def data_sh(repo, env, *args):
    return run([repo / "scripts" / "data.sh", *args], env, cwd=repo)


def calls(log):
    return log.read_text().splitlines()


def docker_calls(log):
    return [line for line in calls(log) if line.startswith("docker ")]


@pytest.mark.parametrize("args", [(), ("local",), ("stg", "--bogus"), ("dev", "--historical")])
def test_rejects_bad_arguments(vm_repo, args):
    repo, env, log = vm_repo
    assert data_sh(repo, env, *args).returncode == 2
    assert docker_calls(log) == []


def test_vm_fetches_then_syncs_with_a_storage_token(vm_repo):
    repo, env, log = vm_repo
    result = data_sh(repo, env, "stg")
    assert result.returncode == 0, result.stderr
    lines = calls(log)
    imds = next(line for line in lines if "169.254.169.254" in line)
    assert "resource=https%3A%2F%2Fstorage.azure.com%2F" in imds
    docker = docker_calls(log)
    assert docker[0].endswith("dsv-data fetch")
    assert docker[1].endswith("dsv-data sync")
    assert len(docker) == 2
    for line in docker:
        assert "-e DSV_STORAGE_ACCOUNT=stdsvstg01" in line
        assert ":/run/secrets/storage-token:ro" in line
        assert "fake-token" not in line  # passed as a file, never on the command line


def test_historical_and_load_flags(vm_repo):
    repo, env, log = vm_repo
    assert data_sh(repo, env, "prod", "--historical", "--load").returncode == 0
    docker = docker_calls(log)
    assert docker[0].endswith("dsv-data fetch --historical")
    assert "stdsvprod01" in docker[0]
    assert docker[-1] == "docker compose run --rm dsv-init-db"


def test_runs_as_calling_user_and_creates_data_dir(vm_repo):
    repo, env, log = vm_repo
    assert data_sh(repo, env, "stg").returncode == 0
    assert (repo / "data").is_dir()
    for line in docker_calls(log):
        assert "--user 1234:5678" in line


def test_token_file_is_removed_afterwards(vm_repo, tmp_path):
    repo, env, log = vm_repo
    env = {**env, "TMPDIR": str(tmp_path / "tmp")}
    (tmp_path / "tmp").mkdir()
    assert data_sh(repo, env, "stg").returncode == 0
    assert list((tmp_path / "tmp").iterdir()) == []


def test_fetch_failure_still_syncs_and_returns_3(vm_repo):
    repo, env, log = vm_repo
    result = data_sh(repo, {**env, "FAKE_FETCH_EXIT": "1"}, "stg", "--load")
    assert result.returncode == 3
    assert "fetch failed" in result.stderr
    docker = docker_calls(log)
    assert docker[1].endswith("dsv-data sync")
    assert docker[-1] == "docker compose run --rm dsv-init-db"


def test_sync_failure_stops_before_load(vm_repo):
    repo, env, log = vm_repo
    result = data_sh(repo, {**env, "FAKE_SYNC_EXIT": "1"}, "stg", "--load")
    assert result.returncode == 1
    assert "dsv-init-db" not in log.read_text()


def test_imds_failure_runs_nothing(vm_repo):
    repo, env, log = vm_repo
    result = data_sh(repo, {**env, "FAKE_IMDS_DOWN": "1"}, "stg")
    assert result.returncode == 1
    assert "IMDS" in result.stderr
    assert docker_calls(log) == []


def test_dev_syncs_only_with_az_token(vm_repo):
    repo, env, log = vm_repo
    result = data_sh(repo, env, "dev")
    assert result.returncode == 0, result.stderr
    assert any(line.startswith("az account get-access-token --resource https://storage.azure.com/")
               for line in calls(log))
    docker = docker_calls(log)
    assert len(docker) == 1 and docker[0].endswith("dsv-data sync")
    assert "stdsvstg01" in docker[0]


def test_dev_without_az_login_explains(vm_repo):
    repo, env, log = vm_repo
    result = data_sh(repo, {**env, "FAKE_AZ_LOGGED_OUT": "1"}, "dev")
    assert result.returncode == 1
    assert "az login" in result.stderr


def test_dev_reads_the_account_from_dev_env(vm_repo):
    repo, env, log = vm_repo
    with open(repo / "deploy" / "dev.env", "a") as f:
        f.write("DSV_STORAGE_ACCOUNT=stdsvdevtest01\n")
    assert data_sh(repo, env, "dev").returncode == 0
    assert "-e DSV_STORAGE_ACCOUNT=stdsvdevtest01" in docker_calls(log)[0]


def test_dev_without_settings_file_names_the_example(vm_repo):
    repo, env, log = vm_repo
    (repo / "deploy" / "dev.env").unlink()
    result = data_sh(repo, env, "dev")
    assert result.returncode == 1
    assert "deploy/dev.env-example" in result.stderr
    assert calls(log) == []


def test_unwritable_data_dir_explains_the_fix(vm_repo):
    # dockerd creates a missing ./data as root when compose runs before data.sh.
    repo, env, log = vm_repo
    (repo / "data").mkdir()
    (repo / "data").chmod(0o555)
    try:
        result = data_sh(repo, env, "stg")
    finally:
        (repo / "data").chmod(0o755)
    assert result.returncode == 1
    assert "chown" in result.stderr
    assert docker_calls(log) == []
