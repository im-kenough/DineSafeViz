"""scripts/fetch-secrets.sh against a fake IMDS and Key Vault (tests/fakes/curl)."""
import os
import stat
import subprocess

from helpers import run


def fetch(repo, env, *args):
    return run([repo / "scripts" / "fetch-secrets.sh", *args], env)


def env_text(repo):
    return (repo / ".env").read_text()


def set_secret(env, name, value):
    with open(os.path.join(env["FAKE_SECRETS_DIR"], name), "w") as f:
        f.write(value)


def test_writes_env_with_settings_secrets_and_compose_file(vm_repo):
    repo, env, _ = vm_repo
    result = fetch(repo, env, "stg")
    assert result.returncode == 0, result.stderr
    text = env_text(repo)
    assert "COMPOSE_FILE=docker-compose.yml:docker-compose.vm.yml\n" in text
    assert "DSV_KEY_VAULT=kv-dsv-stg01\n" in text
    assert "DSV_ANALYTICS_ROOT_URL=https://stg.dinesafeviz.com/analytics/\n" in text
    assert "DSV_DB_PASSWORD='super-secret-1'\n" in text
    assert "DSV_DB_MIGRATOR_PASSWORD='migrator-secret-2'\n" in text
    assert "DSV_DB_APP_PASSWORD='app-secret-3'\n" in text
    assert "DSV_ANALYTICS_ADMIN_PASSWORD='grafana-secret-4'\n" in text
    assert "DSV_TUNNEL_TOKEN='eyJhIjoiZmFrZSJ9'\n" in text


def test_env_file_is_private(vm_repo):
    repo, env, _ = vm_repo
    assert fetch(repo, env, "stg").returncode == 0
    assert stat.S_IMODE(os.stat(repo / ".env").st_mode) == 0o600


def test_prod_reads_the_prod_vault(vm_repo):
    repo, env, log = vm_repo
    assert fetch(repo, env, "prod").returncode == 0
    calls = log.read_text()
    assert "https://kv-dsv-prod01.vault.azure.net/secrets/dsv-db-password?api-version=7.4" in calls
    assert "kv-dsv-stg01" not in calls


def test_rejects_unknown_environment(vm_repo):
    repo, env, log = vm_repo
    result = fetch(repo, env, "local")
    assert result.returncode == 2
    assert "usage" in result.stderr
    assert log.read_text() == ""


def test_missing_secret_leaves_existing_env_untouched(vm_repo):
    repo, env, _ = vm_repo
    (repo / ".env").write_text("OLD=1\n")
    os.remove(os.path.join(env["FAKE_SECRETS_DIR"], "dsv-db-app-password"))
    result = fetch(repo, env, "stg")
    assert result.returncode == 1
    assert "dsv-db-app-password" in result.stderr
    assert "SecretNotFound" in result.stderr
    assert env_text(repo) == "OLD=1\n"
    assert not list(repo.glob(".env.*"))


def test_missing_settings_file_names_the_example(vm_repo):
    repo, env, log = vm_repo
    (repo / "deploy" / "stg.env").unlink()
    result = fetch(repo, env, "stg")
    assert result.returncode == 1
    assert "deploy/stg.env-example" in result.stderr
    assert log.read_text() == ""


def test_firewall_error_names_the_cause(vm_repo):
    repo, env, _ = vm_repo
    result = fetch(repo, env | {"FAKE_KV_ERROR": "ForbiddenByFirewall"}, "stg")
    assert result.returncode == 1
    assert "ForbiddenByFirewall" in result.stderr


# Review focus 2: run off Azure (a laptop) or with IMDS down.
def test_without_imds_fails_fast_and_keeps_env(vm_repo):
    repo, env, _ = vm_repo
    (repo / ".env").write_text("DEV=1\n")
    result = fetch(repo, env | {"FAKE_IMDS_DOWN": "1"}, "stg")
    assert result.returncode == 1
    assert "IMDS" in result.stderr
    assert env_text(repo) == "DEV=1\n"


def test_imds_request_has_a_timeout(vm_repo):
    repo, env, log = vm_repo
    fetch(repo, env, "stg")
    imds = [line for line in log.read_text().splitlines() if "169.254.169.254" in line]
    assert imds and "--max-time" in imds[0]


def test_token_is_never_printed_or_written(vm_repo):
    repo, env, _ = vm_repo
    result = fetch(repo, env, "stg")
    assert "fake-token" not in result.stdout + result.stderr
    assert "fake-token" not in env_text(repo)


# Review focus 1: secret values with shell or URL special characters.
def test_rejects_value_with_single_quote(vm_repo):
    repo, env, _ = vm_repo
    set_secret(env, "dsv-db-password", "it's")
    result = fetch(repo, env, "stg")
    assert result.returncode == 1
    assert "dsv-db-password" in result.stderr
    assert not (repo / ".env").exists()


# The tunnel token is the one secret not generated as hex; it may hold
# base64 characters.
def test_dollar_and_slash_survive_compose_interpolation(vm_repo, tmp_path):
    repo, env, _ = vm_repo
    set_secret(env, "dsv-tunnel-token", "a$b/c+d=")
    assert fetch(repo, env, "stg").returncode == 0
    (repo / "probe.yml").write_text(
        "services:\n  probe:\n    image: alpine\n    environment:\n"
        "      V: ${DSV_TUNNEL_TOKEN}\n"
    )
    result = subprocess.run(
        ["docker", "compose", "--project-directory", str(repo),
         "-f", str(repo / "probe.yml"), "--env-file", str(repo / ".env"),
         "run", "--rm", "--no-deps", "probe", "printenv", "V"],
        capture_output=True, text=True,
        env={"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]},
    )
    # The container sees the exact value. (`config` output would show $$,
    # its own escaping, so check inside a real container instead.)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "a$b/c+d=\n"


# Generated secrets stay URL-safe: / @ : # ? % would corrupt a connection
# string or basic-auth URL silently.
def test_rejects_url_unsafe_generated_secret(vm_repo):
    repo, env, _ = vm_repo
    (repo / ".env").write_text("OLD=1\n")
    set_secret(env, "dsv-analytics-admin-password", "pa/ss@word")
    result = fetch(repo, env, "stg")
    assert result.returncode == 1
    assert "dsv-analytics-admin-password" in result.stderr
    assert "openssl rand -hex 32" in result.stderr
    assert env_text(repo) == "OLD=1\n"


# Review focus 4: .env stays self-contained after a secret refresh.
def test_keeps_image_version_from_previous_env(vm_repo):
    repo, env, _ = vm_repo
    (repo / ".env").write_text("DSV_VERSION=sha-1234567\n")
    assert fetch(repo, env, "stg").returncode == 0
    assert env_text(repo).count("DSV_VERSION=") == 1
    assert "DSV_VERSION=sha-1234567\n" in env_text(repo)


def test_version_from_environment_wins(vm_repo):
    repo, env, _ = vm_repo
    (repo / ".env").write_text("DSV_VERSION=sha-1234567\n")
    assert fetch(repo, env | {"DSV_VERSION": "0.5.0"}, "prod").returncode == 0
    assert env_text(repo).count("DSV_VERSION=") == 1
    assert "DSV_VERSION=0.5.0\n" in env_text(repo)


# Dev has no Key Vault or tunnel: its throwaway secrets are in deploy/dev.env.
def test_dev_writes_env_from_dev_env_without_azure(vm_repo):
    repo, env, log = vm_repo
    result = fetch(repo, env, "dev")
    assert result.returncode == 0, result.stderr
    assert log.read_text() == ""  # no IMDS, no Key Vault
    text = env_text(repo)
    assert "COMPOSE_FILE=docker-compose.yml\n" in text
    assert "DSV_STORAGE_ACCOUNT=stdsvstg01\n" in text
    assert "DSV_ANALYTICS_ROOT_URL=http://localhost:8080/analytics/\n" in text
    assert "DSV_DB_PASSWORD='dev-db-password'\n" in text
    assert "DSV_DB_MIGRATOR_PASSWORD='dev-db-migrator-password'\n" in text
    assert "DSV_DB_APP_PASSWORD='dev-db-app-password'\n" in text
    assert "DSV_ANALYTICS_ADMIN_PASSWORD='dev-analytics-admin-password'\n" in text
    assert "DSV_TUNNEL_TOKEN" not in text
    assert "DSV_KEY_VAULT" not in text
    assert text.count("DSV_DB_PASSWORD=") == 1
    assert stat.S_IMODE(os.stat(repo / ".env").st_mode) == 0o600


def test_dev_missing_secret_names_the_variable(vm_repo):
    repo, env, _ = vm_repo
    (repo / ".env").write_text("OLD=1\n")
    settings = repo / "deploy" / "dev.env"
    settings.write_text("".join(
        line for line in settings.read_text().splitlines(keepends=True)
        if not line.startswith("DSV_DB_APP_PASSWORD=")
    ))
    result = fetch(repo, env, "dev")
    assert result.returncode == 1
    assert "DSV_DB_APP_PASSWORD in deploy/dev.env" in result.stderr
    assert env_text(repo) == "OLD=1\n"


def test_dev_secrets_follow_the_key_vault_rules(vm_repo):
    repo, env, _ = vm_repo
    with open(repo / "deploy" / "dev.env", "a") as f:
        f.write("DSV_ANALYTICS_ADMIN_PASSWORD=pa/ss@word\n")
    result = fetch(repo, env, "dev")
    assert result.returncode == 1
    assert "DSV_ANALYTICS_ADMIN_PASSWORD" in result.stderr
    assert not (repo / ".env").exists()
