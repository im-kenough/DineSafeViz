"""scripts/deploy.sh with fake git, docker, and curl (tests/fakes)."""
import pytest

from helpers import run

SHA = "abc1234def5678900000000000000000000000000"


def deploy(repo, env, *args):
    return run([repo / "scripts" / "deploy.sh", *args], env)


def calls(log):
    return log.read_text().splitlines()


def first(lines, prefix):
    return next(i for i, line in enumerate(lines) if line.startswith(prefix))


def ran(lines, prefix):
    return any(line.startswith(prefix) for line in lines)


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
    assert "docker manifest inspect ghcr.io/im-kenough/dsv-init-db:sha-abc1234" in lines
    assert f"git checkout --quiet --detach {SHA}" in lines
    assert "docker compose pull --quiet" in lines
    assert "docker compose up -d --no-build --remove-orphans" in lines
    assert ("docker compose up -d --no-build --wait --wait-timeout 600 "
            "dsv-tunnel dsv-nginx dsv-app dsv-db dsv-analytics") in lines
    assert "docker compose wait dsv-init-db" in lines
    assert "docker compose wait dsv-init-analytics" in lines
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


# `up --wait` over the whole project fails when a one-shot job that depends on
# another service exits before the wait starts. Jobs are waited on first, and
# --wait only covers the long-running services.
def test_jobs_are_waited_on_before_health_and_wait_skips_them(vm_repo):
    repo, env, log = vm_repo
    assert deploy(repo, env, "stg", "main").returncode == 0
    lines = calls(log)
    up_wait = first(lines, "docker compose up -d --no-build --wait")
    assert first(lines, "docker compose wait dsv-init-analytics") < up_wait
    assert "dsv-init" not in lines[up_wait]


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
    result = deploy(repo, env | {"FAKE_MISSING_IMAGES": "dsv-init-db:sha-abc1234"}, "stg", "main")
    assert result.returncode == 1
    assert "dsv-init-db:sha-abc1234" in result.stderr
    assert "images.yml" in result.stderr
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
def test_failed_data_load_fails_the_deploy_with_its_logs(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {
        "FAKE_INIT_DB_EXIT": "1",
        "FAKE_PS_JSON": '{"Service":"dsv-init-db","State":"exited","ExitCode":1,"Health":""}',
    }, "stg", "main")
    assert result.returncode == 1
    assert "FAILED" in result.stderr
    assert "fake logs for dsv-init-db" in result.stderr
    assert result.stderr.rstrip().endswith("fake logs for dsv-init-db")
    assert not ran(calls(log), "docker image prune")


def test_unhealthy_service_fails_the_deploy_with_its_logs(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {
        "FAKE_UP_WAIT_EXIT": "1",
        "FAKE_PS_JSON": '{"Service":"dsv-app","State":"running","ExitCode":0,"Health":"unhealthy"}',
    }, "stg", "main")
    assert result.returncode == 1
    assert "fake logs for dsv-app" in result.stderr
    assert not ran(calls(log), "docker image prune")


def test_start_failure_skips_the_job_waits(vm_repo):
    repo, env, log = vm_repo
    result = deploy(repo, env | {"FAKE_UP_EXIT": "1"}, "stg", "main")
    assert result.returncode == 1
    assert "FAILED" in result.stderr
    assert not ran(calls(log), "docker compose wait")


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
