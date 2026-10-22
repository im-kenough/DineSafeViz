"""The landing zone bootstrap: gen-imports.sh and the Makefile's bootstrap and
migrate targets, with fake az and terraform (tests/fakes). Nothing reaches
Azure.
"""
import os
import re
import shutil

import pytest

from helpers import FAKES, ROOT, calls, ran, run

INFRA = ROOT / "infra"
GEN_IMPORTS = INFRA / "terraform" / "landing-zone" / "gen-imports.sh"


def subscription_id(env):
    """subscription_id from envs/<env>/env.tfvars, the value check-env and
    gen-imports.sh read."""
    text = (INFRA / "terraform" / "envs" / env / "env.tfvars").read_text()
    return re.search(r'^subscription_id\s*=\s*"([^"]+)"', text, re.M)[1]


STG_OVERRIDE = (
    'terraform {\n  backend "local" {\n'
    '    path = "../envs/stg/landing-zone.bootstrap.tfstate"\n  }\n}\n'
)


@pytest.fixture
def fake_env(tmp_path):
    """PATH with the fakes first, and the log they append to."""
    log = tmp_path / "calls.log"
    log.touch()
    env = {
        "PATH": f"{FAKES}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "FAKE_LOG": str(log),
    }
    return env, log


@pytest.fixture
def infra(tmp_path):
    """A copy of infra/, so an override written here never touches a real
    bootstrap in progress in the checkout."""
    copy = tmp_path / "infra"
    shutil.copytree(
        INFRA,
        copy,
        ignore=shutil.ignore_patterns(".terraform*", "*.tfstate*", "*.tfplan*", "*_override.tf", "imports.tf"),
    )
    return copy


@pytest.mark.parametrize("args", [[], ["stg", "prod"], ["qa"]])
def test_gen_imports_usage(fake_env, args):
    env, log = fake_env
    result = run([GEN_IMPORTS, *args], env)
    assert result.returncode == 2
    assert result.stderr.startswith("Usage:")
    assert result.stdout == ""
    assert calls(log) == []


def test_gen_imports_keys_match_rbac():
    text = GEN_IMPORTS.read_text()
    heredoc = re.search(r"<<EOF\n(.*?)\nEOF\n", text, re.S)
    assert heredoc
    keys = [line.split("|", 1)[0] for line in heredoc[1].splitlines()]
    assert keys == ["operators-contributor-core", "operators-kv-secrets-officer", "operators-blob-reader-dinesafe"]
    rbac = (INFRA / "terraform" / "landing-zone" / "rbac.tf").read_text()
    defined = set(re.findall(r"^\s*([a-z-]+)\s*=\s*\{", rbac[rbac.index("role_assignments = merge("):], re.M))
    assert set(keys) <= defined


IMPORT = re.compile(r'import \{\n  to = (\S+)\n  id = "([^"\n]+)"\n\}\n\n')


def test_gen_imports_blocks(fake_env):
    env, log = fake_env
    result = run([GEN_IMPORTS, "stg"], env | {"FAKE_AZ_MISSING_ROLE": "Storage Blob Data Reader"})
    assert result.returncode == 0, result.stderr
    # The output is nothing but well-formed import blocks.
    assert IMPORT.sub("", result.stdout) == ""
    blocks = dict(IMPORT.findall(result.stdout))
    sub = subscription_id("stg")
    rg = f"/subscriptions/{sub}/resourceGroups/rg-dsv-stg01"
    assignment = "/providers/Microsoft.Authorization/roleAssignments/00000000-0000-0000-0000-000000000001"
    assert blocks == {
        "azuread_group.operators": "/groups/00000000-0000-0000-0000-000000000000",
        "azurerm_consumption_budget_subscription.monthly":
            f"/subscriptions/{sub}/providers/Microsoft.Consumption/budgets/budget-dsv-stg01-monthly",
        'azurerm_role_assignment.this["operators-contributor-core"]': rg + assignment,
        'azurerm_role_assignment.this["operators-kv-secrets-officer"]':
            f"{rg}/providers/Microsoft.KeyVault/vaults/kv-dsv-stg01{assignment}",
    }
    lines = calls(log)
    assert ran(lines, "az ad group show --group sg-dsv-stg01-operators")
    assert sum(line.startswith("az role assignment list") for line in lines) == 3
    assert not any(re.search(r"\b(create|delete|update|set)\b", line) for line in lines)


def test_bootstrap_refuses_while_one_is_in_progress(infra, fake_env):
    env, log = fake_env
    override = infra / "terraform" / "landing-zone" / "backend_override.tf"
    override.write_text(STG_OVERRIDE)
    result = run(["make", "-C", infra, "bootstrap", "ENV=prod"], env | {"FAKE_AZ_SUBSCRIPTION": subscription_id("prod")})
    override.unlink()
    assert result.returncode != 0
    assert "ERROR: a bootstrap is already in progress:" in result.stderr
    assert "../envs/stg/landing-zone.bootstrap.tfstate" in result.stderr
    assert calls(log) == []
    assert not (infra / "terraform" / "landing-zone" / "imports.tf").exists()


def test_migrate_refuses_another_envs_bootstrap(infra, fake_env):
    env, log = fake_env
    override = infra / "terraform" / "landing-zone" / "backend_override.tf"
    override.write_text(STG_OVERRIDE)
    result = run(["make", "-C", infra, "migrate", "ENV=prod"], env | {"FAKE_AZ_SUBSCRIPTION": subscription_id("prod")})
    assert result.returncode != 0
    assert "ERROR: the bootstrap in progress isn't for ENV=prod." in result.stderr
    assert override.read_text() == STG_OVERRIDE
    override.unlink()
    assert not any(line.startswith("terraform") for line in calls(log))


def test_help_lists_bootstrap_and_migrate():
    result = run(["make", "-C", INFRA, "help"], {"PATH": os.environ["PATH"]})
    assert result.returncode == 0
    targets = re.findall(r"^  (\S+)", result.stdout, re.M)
    assert "bootstrap" in targets
    assert "migrate" in targets


HOWTO = ROOT / "docs-new" / "how-to" / "initial-setup" / "bootstrap-landing-zone.md"


def test_howto_links_resolve():
    links = re.findall(r"\]\(([^)#]+)\)", HOWTO.read_text())
    assert "../../../docs/ref/iam.md" in links
    assert "../../ref/6-azure-resources.md" in links
    for link in links:
        assert (HOWTO.parent / link).resolve().is_file(), link
