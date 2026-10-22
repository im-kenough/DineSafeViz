"""Static checks of the landing zone layer's state settings (no terraform needed)."""
import re
import subprocess

import pytest

from helpers import ROOT

TF = ROOT / "infra" / "terraform"
LZ = TF / "landing-zone"


def settings(path):
    """Top-level `key = value` pairs of a flat HCL file, comments stripped."""
    pairs = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            key, value = (part.strip() for part in line.split("=", 1))
            pairs[key] = value
    return pairs


def resource_body(text, rtype, name):
    """Body of `resource "rtype" "name" { ... }`, matched by brace depth."""
    match = re.search(rf'resource "{rtype}" "{name}" {{', text)
    assert match, f"{rtype}.{name} not found"
    depth, start = 1, match.end()
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i]
    raise AssertionError(f"{rtype}.{name} is not closed")


@pytest.mark.parametrize("env, account", [("stg", "stdsvstg01tfstate"), ("prod", "stdsvprod01tfstate")])
def test_backend_points_at_landing_zone_container(env, account):
    backend = settings(TF / "envs" / env / "landing-zone.backend.hcl")
    assert backend == {
        "storage_account_name": f'"{account}"',
        "container_name": '"tfstate-landing-zone"',
        "key": '"landing-zone.tfstate"',
        "use_azuread_auth": "true",
    }


@pytest.mark.parametrize("env", ["stg", "prod"])
def test_tfvars_locks_and_budget(env):
    tfvars = settings(TF / "envs" / env / "landing-zone.tfvars")
    assert tfvars["lock_iac_rg"] == "true"
    assert tfvars["lock_core_rg"] == "false"
    assert tfvars["budget_amount"] == "40"
    # The budget email lives only in the gitignored secret tfvars.
    assert "budget_contact_emails" not in tfvars


def test_state_account_is_entra_only():
    body = resource_body((LZ / "state.tf").read_text(), "azurerm_storage_account", "tfstate")
    assert re.search(r"^\s*shared_access_key_enabled\s*=\s*false\s*$", body, re.M)


@pytest.mark.parametrize("name", ["tfstate", "landing_zone"])
def test_state_containers_are_private(name):
    body = resource_body((LZ / "state.tf").read_text(), "azurerm_storage_container", name)
    assert re.search(r'^\s*container_access_type\s*=\s*"private"\s*$', body, re.M)


def block_body(text, header):
    """Body of the first block whose opening line is `header {`."""
    match = re.search(rf"{re.escape(header)} {{", text)
    assert match, f"{header} not found"
    depth, start = 1, match.end()
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i]
    raise AssertionError(f"{header} is not closed")


def role_assignments():
    """Each `key = { ... }` entry of local.role_assignments, by key."""
    text = (LZ / "rbac.tf").read_text()
    start = text.index("role_assignments = merge(")
    return dict(re.findall(r"^\s*([a-z-]+)\s*=\s*(\{.*\})\s*$", text[start:], re.M))


ROLE_DEFINITION_IDS = {
    "4633458b-17de-408a-b874-0445c86b69e6",
    "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",
    "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
}
SUBSCRIPTION_IDS = {
    "53db2ec0-9b36-42d0-aa0d-7745f6dafe9a",
    "a3c53ab4-7208-4b24-bddb-2118dd7b2206",
}
GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


@pytest.mark.parametrize("name", ["plan", "apply"])
def test_federated_credentials(name):
    body = resource_body((LZ / "identities.tf").read_text(), "azurerm_federated_identity_credential", name)
    settings_ = dict(re.findall(r"^\s*(\w+)\s*=\s*(.+?)\s*$", body, re.M))
    assert settings_["issuer"] == '"https://token.actions.githubusercontent.com"'
    assert settings_["audience"] == '["api://AzureADTokenExchange"]'
    assert settings_["subject"] == f'"repo:im-kenough/DineSafeViz:environment:${{var.env}}-{name}"'
    assert settings_["user_assigned_identity_id"] == f"azurerm_user_assigned_identity.{name}.id"


def test_role_assignment_keys():
    keys = set(role_assignments())
    base = {
        "operators-contributor-core",
        "operators-contributor-compute",
        "operators-rbac-admin-core",
        "operators-kv-secrets-officer",
        "operators-blob-contributor-tfstate",
        "apply-contributor-core",
        "apply-contributor-compute",
        "apply-rbac-admin-core",
        "apply-blob-contributor-tfstate",
        "plan-reader-core",
        "plan-reader-compute",
        "plan-blob-reader-tfstate",
        "admin-blob-contributor-landing-zone",
    }
    assert keys == base | {"operators-blob-reader-dinesafe"}
    # The dinesafe reader is the only conditional entry, and only for stg.
    text = (LZ / "rbac.tf").read_text()
    conditional = re.search(r'var\.env == "stg" \? \{(.*?)\} : \{\}', text, re.S)
    assert conditional
    assert re.findall(r"^\s*([a-z-]+)\s*=", conditional[1], re.M) == ["operators-blob-reader-dinesafe"]


def test_no_assignment_in_iac_rg_except_admin_state():
    entries = role_assignments()
    for key, entry in entries.items():
        assert "azurerm_resource_group.iac" not in entry, key
    assert [k for k, e in entries.items() if "landing_zone_container_id" in e] == [
        "admin-blob-contributor-landing-zone"
    ]
    assert "azurerm_resource_group.iac" not in (LZ / "rbac.tf").read_text()


def test_rbac_admin_condition():
    text = (LZ / "rbac.tf").read_text()
    roles = re.search(r'delegable_role_ids = join\(", ", \[(.*?)\]\)', text, re.S)
    assert roles
    assert sorted(GUID.findall(roles[1])) == sorted(ROLE_DEFINITION_IDS)
    condition = re.search(r"rbac_admin_condition = trimspace\(<<-EOT\n(.*?)\n\s*EOT\n\s*\)", text, re.S)
    assert condition
    condition = condition[1]
    for action in ("write", "delete"):
        assert f"!(ActionMatches{{'Microsoft.Authorization/roleAssignments/{action}'}})" in condition
    for source in ("Request", "Resource"):
        assert (
            f"@{source}[Microsoft.Authorization/roleAssignments:PrincipalType] "
            "ForAnyOfAnyValues:StringEqualsIgnoreCase {'ServicePrincipal'}"
        ) in condition
        assert (
            f"@{source}[Microsoft.Authorization/roleAssignments:RoleDefinitionId] "
            "ForAnyOfAnyValues:GuidEquals {${local.delegable_role_ids}}"
        ) in condition
    # Only the two RBAC Administrator assignments carry the condition.
    conditioned = [k for k, e in role_assignments().items() if "condition = local.rbac_admin_condition" in e]
    assert conditioned == ["operators-rbac-admin-core", "apply-rbac-admin-core"]


def test_budget_emails_are_sensitive():
    text = (LZ / "variables.tf").read_text()
    body = block_body(text, 'variable "budget_contact_emails"')
    assert re.search(r"^\s*sensitive\s*=\s*true\s*$", body, re.M)


@pytest.mark.parametrize("env", ["stg", "prod"])
def test_secret_tfvars_example(env):
    path = TF / "envs" / env / "landing-zone.secret.tfvars.example"
    assert settings(path) == {"budget_contact_emails": '["you@example.com"]'}
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path.relative_to(ROOT)], cwd=ROOT
    )
    assert result.returncode == 1
    # The real file next to it stays ignored.
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path.with_suffix("").relative_to(ROOT)], cwd=ROOT
    )
    assert result.returncode == 0


def test_outputs():
    text = (LZ / "outputs.tf").read_text()
    assert re.findall(r'^output "(\w+)"', text, re.M) == [
        "plan_client_id",
        "apply_client_id",
        "tenant_id",
        "subscription_id",
        "state_account_name",
    ]


def test_budget():
    body = resource_body((LZ / "main.tf").read_text(), "azurerm_consumption_budget_subscription", "monthly")
    assert re.search(r"^\s*amount\s*=\s*var\.budget_amount\s*$", body, re.M)
    assert re.search(r"^\s*contact_emails\s*=\s*var\.budget_contact_emails\s*$", body, re.M)
    thresholds = re.findall(r'\{ type = "(\w+)", threshold = (\d+) \}', body)
    assert thresholds == [("Actual", "50"), ("Actual", "80"), ("Actual", "100"), ("Forecasted", "100")]


def committed_files():
    """Files under infra/terraform that git tracks or would add (not ignored)."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "infra/terraform"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [ROOT / line for line in out.splitlines() if (ROOT / line).is_file()]


def test_no_ids_or_addresses_committed():
    files = committed_files()
    assert files
    for path in files:
        text = path.read_text(errors="replace")
        extra = {g.lower() for g in GUID.findall(text)} - ROLE_DEFINITION_IDS - SUBSCRIPTION_IDS
        assert not extra, f"{path}: {extra}"
        for address in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text):
            assert address.endswith("@example.com"), f"{path}: {address}"
    # Subscription IDs belong only in env.tfvars.
    for path in files:
        if path.name != "env.tfvars":
            assert not SUBSCRIPTION_IDS & set(GUID.findall(path.read_text(errors="replace"))), path
