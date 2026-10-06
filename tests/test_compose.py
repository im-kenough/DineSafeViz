"""Static checks of the merged Compose config (docker compose config)."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from helpers import ROOT, run

COMPOSE_DIR = Path(__file__).resolve().parent / "compose"


def compose_config(env_file, *files, profiles=()):
    cmd = ["docker", "compose", "--project-directory", str(ROOT), "--env-file", str(env_file)]
    for name in files:
        cmd += ["-f", str(ROOT / name)]
    for profile in profiles:
        cmd += ["--profile", profile]
    cmd += ["config", "--format", "json"]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]},
    )


def load(env_file, *files, profiles=()):
    result = compose_config(env_file, *files, profiles=profiles)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# Profile services (dsv-data) are left out of `config` unless their profile is on.
@pytest.fixture(scope="module")
def local():
    return load(COMPOSE_DIR / "local.env-test", "docker-compose.yml", profiles=("data",))


def test_local_db_role_passwords_default_to_todays_values(local):
    env = local["services"]["dsv-db"]["environment"]
    assert env["DSV_DB_APP_PASSWORD"] == "dinesafe_app"
    assert env["DSV_DB_MIGRATOR_PASSWORD"] == "dinesafe_migrator"


def test_local_db_runs_set_passwords_after_init_sql(local):
    targets = sorted(
        v["target"]
        for v in local["services"]["dsv-db"]["volumes"]
        if v["target"].startswith("/docker-entrypoint-initdb.d/")
    )
    # The image runs these in name order: init.sql creates the roles first.
    assert targets == [
        "/docker-entrypoint-initdb.d/init.sql",
        "/docker-entrypoint-initdb.d/set-passwords.sh",
    ]


LONG_RUNNING = ["dsv-tunnel", "dsv-nginx", "dsv-app", "dsv-db", "dsv-analytics"]
ONE_SHOT = ["dsv-init-db", "dsv-data"]
VM_FILES = ("docker-compose.yml", "docker-compose.vm.yml")


@pytest.fixture(scope="module")
def vm():
    return load(COMPOSE_DIR / "vm.env-test", *VM_FILES, profiles=("data",))


def test_local_stack_is_unaffected_by_the_vm_file(local):
    services = local["services"]
    assert "dsv-tunnel" not in services
    assert [p["published"] for p in services["dsv-nginx"]["ports"]] == ["8080"]
    assert [p["published"] for p in services["dsv-analytics"]["ports"]] == ["3000"]
    assert "build" in services["dsv-app"]
    assert "build" in services["dsv-init-db"]


def test_vm_uses_published_images(vm):
    services = vm["services"]
    assert services["dsv-app"]["image"] == "ghcr.io/im-kenough/dsv-app:test-version"
    assert services["dsv-init-db"]["image"] == "ghcr.io/im-kenough/dsv-init-db:test-version"
    assert services["dsv-data"]["image"] == "ghcr.io/im-kenough/dsv-init-db:test-version"
    assert services["dsv-tunnel"]["image"] == "cloudflare/cloudflared:2026.10.0"


@pytest.mark.parametrize("name", LONG_RUNNING)
def test_vm_long_running_services_restart_and_are_hardened(vm, name):
    svc = vm["services"][name]
    assert svc["restart"] == "unless-stopped"
    assert "no-new-privileges:true" in svc["security_opt"]
    assert svc["logging"] == {
        "driver": "json-file",
        "options": {"max-size": "10m", "max-file": "3"},
    }
    assert "mem_limit" in svc


@pytest.mark.parametrize("name", ONE_SHOT)
def test_vm_one_shot_jobs_run_once(vm, name):
    svc = vm["services"][name]
    assert svc["restart"] == "no"
    assert "no-new-privileges:true" in svc["security_opt"]
    assert "mem_limit" in svc


def test_vm_publishes_no_ports(vm):
    for name, svc in vm["services"].items():
        assert not svc.get("ports"), name


def test_vm_networks(vm):
    networks = vm["networks"]
    assert networks["backend"]["internal"] is True
    assert not networks["edge"].get("internal")
    assert not networks["egress"].get("internal")
    assert {name: set(svc["networks"]) for name, svc in vm["services"].items()} == {
        "dsv-tunnel": {"edge"},
        "dsv-nginx": {"edge", "backend"},
        "dsv-app": {"backend"},
        "dsv-db": {"backend"},
        "dsv-analytics": {"backend"},
        "dsv-init-db": {"backend"},
        "dsv-data": {"egress"},
    }


def test_vm_grafana_has_a_fixed_admin_address(vm):
    backend = vm["services"]["dsv-analytics"]["networks"]["backend"]
    assert backend["ipv4_address"] == "172.30.10.30"


@pytest.mark.parametrize("name", ["dsv-app", "dsv-tunnel"])
def test_vm_read_only_services(vm, name):
    svc = vm["services"][name]
    assert svc["read_only"] is True
    assert svc["cap_drop"] == ["ALL"]
    assert "/tmp" in svc["tmpfs"]


def test_vm_minimal_capabilities(vm):
    services = vm["services"]
    assert services["dsv-nginx"]["cap_drop"] == ["ALL"]
    assert set(services["dsv-nginx"]["cap_add"]) == {
        "CHOWN", "DAC_OVERRIDE", "NET_BIND_SERVICE", "SETGID", "SETUID"}
    assert services["dsv-db"]["cap_drop"] == ["ALL"]
    assert set(services["dsv-db"]["cap_add"]) == {
        "CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"}


def test_vm_secrets_come_from_env_not_local_defaults(vm):
    services = vm["services"]
    assert services["dsv-app"]["environment"]["DSV_DB_PASSWORD"] == "test-app-pw"
    assert services["dsv-analytics"]["environment"]["DSV_DB_PASSWORD"] == "test-app-pw"
    assert services["dsv-db"]["environment"]["DSV_DB_APP_PASSWORD"] == "test-app-pw"
    assert services["dsv-db"]["environment"]["DSV_DB_MIGRATOR_PASSWORD"] == "test-migrator-pw"
    assert services["dsv-tunnel"]["environment"]["TUNNEL_TOKEN"] == "test-tunnel-token"


def test_vm_grafana_settings(vm):
    env = vm["services"]["dsv-analytics"]["environment"]
    assert env["GF_SERVER_ROOT_URL"] == "https://stg.example.test/analytics/"
    assert env["GF_USERS_VIEWERS_CAN_EDIT"] == "false"
    assert env["GF_AUTH_ANONYMOUS_HIDE_VERSION"] == "true"
    assert env["GF_SECURITY_COOKIE_SECURE"] == "true"
    assert env["GF_ANALYTICS_REPORTING_ENABLED"] == "false"
    assert env["GF_ANALYTICS_CHECK_FOR_UPDATES"] == "false"
    assert env["GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES"] == "false"


def test_vm_nginx_mounts_the_snippets(vm):
    targets = {v["target"] for v in vm["services"]["dsv-nginx"]["volumes"]}
    assert "/etc/nginx/snippets" in targets


@pytest.mark.parametrize("var", [
    "DSV_VERSION", "DSV_DB_PASSWORD", "DSV_DB_APP_PASSWORD", "DSV_DB_MIGRATOR_PASSWORD",
    "DSV_ANALYTICS_ADMIN_PASSWORD", "DSV_ANALYTICS_ROOT_URL", "DSV_TUNNEL_TOKEN",
])
def test_vm_refuses_to_start_without_required_values(tmp_path, var):
    lines = [
        line for line in (COMPOSE_DIR / "vm.env-test").read_text().splitlines()
        if not line.startswith(f"{var}=")
    ]
    env_file = tmp_path / "vm.env-test"
    env_file.write_text("\n".join(lines) + "\n")
    result = compose_config(env_file, *VM_FILES)
    assert result.returncode != 0
    assert var in result.stderr


def test_vm_init_db_memory_covers_the_measured_peak(vm):
    # refresh.py peaked at about 430 MiB on the full data load (October 5,
    # 2026). Below that, the kernel kills it with exit 137.
    assert int(vm["services"]["dsv-init-db"]["mem_limit"]) >= 512 * 1024 * 1024


def test_vm_tunnel_serves_readiness_for_deploy_sh(vm):
    # deploy.sh asks http://dsv-tunnel:2000/ready from dsv-nginx (edge network).
    assert vm["services"]["dsv-tunnel"]["environment"]["TUNNEL_METRICS"] == "0.0.0.0:2000"


def test_data_runs_only_when_asked():
    plain = load(COMPOSE_DIR / "local.env-test", "docker-compose.yml")
    assert "dsv-data" not in plain["services"]


def test_data_service_runs_data_py_and_owns_the_mirror(local):
    svc = local["services"]["dsv-data"]
    assert svc["entrypoint"] == ["python3", "data.py"]
    mounts = {v["target"]: v for v in svc["volumes"]}
    assert mounts["/data"]["source"] == str(ROOT / "data")
    assert not mounts["/data"].get("read_only")
    assert "DSV_DB_PASSWORD" not in svc.get("environment", {})


def test_init_db_reads_the_mirror_read_only(local):
    svc = local["services"]["dsv-init-db"]
    mounts = {v["target"]: v for v in svc["volumes"]}
    assert mounts["/data"]["source"] == str(ROOT / "data")
    assert mounts["/data"]["read_only"] is True
    assert svc["environment"]["DSV_DATA_DIR"] == "/data"


def test_nothing_mounts_the_old_csv_folder(local, vm):
    for config in (local, vm):
        for name, svc in config["services"].items():
            for v in svc.get("volumes", []):
                assert "local-data" not in v.get("source", ""), name


def test_vm_data_service_is_hardened(vm):
    svc = vm["services"]["dsv-data"]
    assert svc["read_only"] is True
    assert svc["cap_drop"] == ["ALL"]
    assert "/tmp" in svc["tmpfs"]
    assert int(svc["mem_limit"]) <= 384 * 1024 * 1024


# The .env that `fetch-secrets.sh dev` writes drives the local stack, so the
# dev passwords replace the built-in defaults everywhere they're used.
def test_dev_env_reaches_every_service(vm_repo):
    repo, env, _ = vm_repo
    result = run([repo / "scripts" / "fetch-secrets.sh", "dev"], env)
    assert result.returncode == 0, result.stderr
    services = load(repo / ".env", "docker-compose.yml")["services"]
    assert "dsv-tunnel" not in services
    db = services["dsv-db"]["environment"]
    assert db["POSTGRES_USER"] == "dsv_admin"
    assert db["POSTGRES_PASSWORD"] == "dev-db-password"
    assert db["DSV_DB_APP_PASSWORD"] == "dev-db-app-password"
    assert db["DSV_DB_MIGRATOR_PASSWORD"] == "dev-db-migrator-password"
    assert services["dsv-init-db"]["environment"]["DSV_DB_PASSWORD"] == "dev-db-password"
    for name in ("dsv-app", "dsv-analytics"):
        assert services[name]["environment"]["DSV_DB_PASSWORD"] == "dev-db-app-password"
    grafana = services["dsv-analytics"]["environment"]
    assert grafana["GF_SECURITY_ADMIN_PASSWORD"] == "dev-analytics-admin-password"
    assert grafana["GF_SERVER_ROOT_URL"] == "http://localhost:8080/analytics/"
