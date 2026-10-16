"""scripts/deploy.sh with fake git, docker, and curl (tests/fakes)."""
import pytest

from helpers import MIGRATE, calls, first, ran, run

SHA = "abc1234def5678900000000000000000000000000"


def deploy(repo, env, *args):
    return run([repo / "scripts" / "deploy.sh", *args], env)


@pytest.mark.parametrize("args", [
    ("stg", "v1.2.3"), ("prod", "main"), ("prod", "v1.2"), ("prod", "1.2.3"),
    ("dev", "main"), ("stg",), (),
])
def test_rejects_bad_arguments(vm_repo, args):
    repo, env, log = vm_repo
    result = deploy(repo, env, *args)
    assert result.returncode == 2
    assert "usage" in result.stderr
    assert calls(log) == []


def test_stg_deploys_main_by_its_commit_tag(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env, "stg", "main")
    assert result.returncode == 0, result.stderr
    lines = calls(log)
    assert "git rev-parse --verify --quiet origin/main^{commit}" in lines
    assert "docker manifest inspect ghcr.io/im-kenough/dsv-app:sha-abc1234" in lines
    assert "docker manifest inspect ghcr.io/im-kenough/dsv-pipeline:sha-abc1234" in lines
    assert f"git checkout --quiet --detach {SHA}" in lines
    assert "docker compose --profile pipeline pull --quiet" in lines
    assert "docker compose up -d --no-build --remove-orphans --wait --wait-timeout 600" in lines
    assert len([line for line in lines if line.startswith("docker compose up")]) == 1
    assert ran(lines, "docker image prune")
    assert "DSV_VERSION=sha-abc1234\n" in (repo / ".env").read_text()
    assert "kv-dsv-stg01" in log.read_text()
    assert "stg is running sha-abc1234" in result.stdout


def test_images_are_checked_before_checkout_secrets_and_start(vm_repo):
    repo, env, log = vm_repo
    assert deploy(repo, env, "stg", "main").returncode == 0
    lines = calls(log)
    assert (
        first(lines, "docker manifest inspect")
        < first(lines, "git checkout")
        < first(lines, "curl")
        < first(lines, "docker compose up")
    )


def test_missing_settings_file_stops_before_checkout(vm_repo):
    repo, env, log = vm_repo
    (repo / "deploy" / "stg.env").unlink()
    result = deploy(repo, env, "stg", "main")
    assert result.returncode == 1
    assert "deploy/stg.env-example" in result.stderr
    assert not ran(calls(log), "git")


def test_prod_deploys_a_release_tag(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env, "prod", "v1.2.3")
    assert result.returncode == 0, result.stderr
    lines = calls(log)
    assert "git rev-parse --verify --quiet refs/tags/v1.2.3^{commit}" in lines
    assert "docker manifest inspect ghcr.io/im-kenough/dsv-app:1.2.3" in lines
    assert "DSV_VERSION=1.2.3\n" in (repo / ".env").read_text()
    assert "kv-dsv-prod01" in log.read_text()


def test_unknown_tag_stops_before_anything(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_GIT_MISSING_REF": "1"}, "prod", "v9.9.9")
    assert result.returncode == 1
    assert "v9.9.9" in result.stderr
    lines = calls(log)
    assert not ran(lines, "docker")
    assert not ran(lines, "git checkout")


def test_missing_image_stops_before_changing_anything(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_MISSING_IMAGES": "dsv-pipeline:sha-abc1234"}, "stg", "main")
    assert result.returncode == 1
    assert "dsv-pipeline:sha-abc1234" in result.stderr
    assert "ci.yml" in result.stderr
    lines = calls(log)
    assert not ran(lines, "git checkout")
    assert not ran(lines, "curl")
    assert not ran(lines, "docker compose")
    assert not (repo / ".env").exists()


# Review focus 3: a dirty or diverged checkout on the VM.
def test_failed_checkout_stops_before_containers_change(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_GIT_CHECKOUT_FAIL": "1"}, "stg", "main")
    assert result.returncode == 1
    assert "checkout" in result.stderr
    lines = calls(log)
    assert not ran(lines, "curl")
    assert not ran(lines, "docker compose")


# Review focus 5: the data load fails after --wait returns.
def test_unhealthy_service_fails_the_deploy_with_its_logs(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {
        "FAKE_UP_EXIT": "1",
        "FAKE_PS_JSON": '{"Service":"dsv-app","State":"running","ExitCode":0,"Health":"unhealthy"}',
    }, "stg", "main")
    assert result.returncode == 1
    assert "fake logs for dsv-app" in result.stderr
    assert not ran(calls(log), "docker image prune")


def test_start_failure_skips_the_data_load(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_UP_EXIT": "1"}, "stg", "main")
    assert result.returncode == 1
    assert "FAILED" in result.stderr
    assert not ran(calls(log), "docker compose --profile pipeline run")


# Review focus 4: repeated deploys keep .env self-contained.
def test_repeated_deploys_keep_one_version_line(vm_repo):
    repo, env, _ = vm_repo
    assert deploy(repo, env, "stg", "main").returncode == 0
    second = env | {"FAKE_GIT_SHA": "def5678abc0000000000000000000000000000000"}
    assert deploy(repo, second, "stg", "main").returncode == 0
    text = (repo / ".env").read_text()
    assert text.count("DSV_VERSION=") == 1
    assert "DSV_VERSION=sha-def5678\n" in text
    assert text.count("COMPOSE_FILE=") == 1


# A tunnel's logs grow between deploys, and grep -q on a long docker logs
# stream fails under pipefail. Readiness comes from cloudflared's /ready.
def test_tunnel_readiness_comes_from_its_ready_endpoint(vm_repo):
    repo, env, log = vm_repo
    assert deploy(repo, env, "stg", "main").returncode == 0
    lines = calls(log)
    assert ("docker compose exec -T dsv-nginx wget -q -O /dev/null "
            "http://dsv-tunnel:2000/ready") in lines
    assert not ran(lines, "docker compose logs")


def test_tunnel_not_ready_fails_the_deploy_with_its_logs(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_TUNNEL_NOT_READY": "1"}, "stg", "main")
    assert result.returncode == 1
    assert result.stderr.rstrip().endswith("fake logs for dsv-tunnel")
    assert not ran(calls(log), "docker image prune")


# Review focus 3: local edits that don't conflict with the target commit
# would survive the checkout and run under the new version's name.
def test_dirty_tree_stops_before_anything_changes(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_GIT_DIRTY": " M docker-compose.vm.yml"}, "stg", "main")
    assert result.returncode == 1
    assert "docker-compose.vm.yml" in result.stderr
    lines = calls(log)
    assert not ran(lines, "git checkout")
    assert not ran(lines, "docker")
    assert not ran(lines, "curl")


def test_smoke_check_confirms_containers_cannot_reach_imds(vm_repo):
    repo, env, log = vm_repo
    assert deploy(repo, env, "stg", "main").returncode == 0
    # IMDS answers 400 without these, which a bare wget would read as blocked.
    imds = [line for line in calls(log)
            if "169.254.169.254" in line and line.startswith("docker compose exec")]
    assert len(imds) == 1
    assert "Metadata: true" in imds[0]
    assert "api-version=" in imds[0]


def test_reachable_imds_fails_the_deploy(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, {**env, "FAKE_IMDS_REACHABLE": "1"}, "stg", "main")
    assert result.returncode != 0
    assert "IMDS" in result.stderr


def test_dev_builds_and_starts_the_working_tree(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env, "dev")
    assert result.returncode == 0, result.stderr
    lines = calls(log)
    assert not ran(lines, "git")  # deploys the working tree as it is
    assert not ran(lines, "curl")  # no IMDS or Key Vault
    assert not ran(lines, "docker manifest")
    assert not ran(lines, "docker compose pull")
    assert not ran(lines, "docker image prune")  # not on a workstation
    assert (
        first(lines, "docker compose up -d --build --remove-orphans --wait")
        < first(lines, MIGRATE)
        < first(lines, "az account get-access-token")
        < first(lines, "docker compose --profile pipeline run")
    )
    assert ("docker compose exec -T dsv-nginx wget -q -O /dev/null "
            "http://127.0.0.1/healthz") in lines
    assert "DSV_DB_PASSWORD='dev-db-password'\n" in (repo / ".env").read_text()
    assert "http://localhost:8080" in result.stdout


LOAD = "docker compose --profile pipeline run"


def test_data_loads_after_the_stack_is_healthy_and_migrated(vm_repo):
    repo, env, log = vm_repo
    assert deploy(repo, env, "stg", "main").returncode == 0
    lines = calls(log)
    assert (
        first(lines, "docker compose --profile pipeline pull")
        < first(lines, "docker compose up -d --no-build --remove-orphans --wait")
        < first(lines, MIGRATE)
        < first(lines, LOAD)
        < first(lines, "docker image prune")
    )
    # load, never run or ingest: deploys never contact Toronto Open Data.
    assert lines[first(lines, LOAD)].endswith("dsv-pipeline load")


def test_failed_migration_fails_the_deploy_before_loading(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_MIGRATE_EXIT": "1"}, "stg", "main")
    assert result.returncode == 1
    assert "fake logs for dsv-db" in result.stderr
    assert not ran(calls(log), LOAD)


def test_failed_load_with_data_warns_and_keeps_serving(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_PIPELINE_EXIT": "1", "FAKE_DB_HAS_ROWS": "t"}, "stg", "main")
    assert result.returncode == 0, result.stderr
    assert "serving the data already in the database" in result.stderr


def test_failed_load_into_an_empty_database_fails_the_deploy(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_PIPELINE_EXIT": "1", "FAKE_DB_HAS_ROWS": "f"}, "stg", "main")
    assert result.returncode == 1
    assert "empty database" in result.stderr
    assert not ran(calls(log), "docker image prune")


# Review focus 5: compose run --rm leaves no container using the pipeline
# image, so prune -a deletes it.
def test_pipeline_image_is_pulled_again_after_prune(vm_repo):
    repo, env, log = vm_repo
    assert deploy(repo, env, "stg", "main").returncode == 0
    lines = calls(log)
    prune = first(lines, "docker image prune")
    assert "docker compose --profile pipeline pull --quiet dsv-pipeline" in lines[prune + 1:]


def test_dev_without_az_login_and_an_empty_database_fails(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_AZ_LOGGED_OUT": "1", "FAKE_DB_HAS_ROWS": "f"}, "dev")
    assert result.returncode == 1
    assert "az login" in result.stderr


def test_dev_without_az_login_keeps_existing_data(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_AZ_LOGGED_OUT": "1"}, "dev")
    assert result.returncode == 0, result.stderr
    assert "serving the data already in the database" in result.stderr
