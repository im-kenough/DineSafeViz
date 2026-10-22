"""Static checks of the landing zone layer's state settings (no terraform needed)."""
import re

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
