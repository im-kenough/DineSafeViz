#!/usr/bin/env python3
"""Merge Ansible group_vars/all.yml and secrets from stdin, output HCL for Packer/Terraform.

Usage:
    ansible-vault view vault/secrets.yml --ask-vault-pass | python3 scripts/render-vars.py packer
    ansible-vault view vault/secrets.yml --ask-vault-pass | python3 scripts/render-vars.py terraform
"""

import sys
import yaml
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ALL_VARS_PATH = os.path.join(SCRIPT_DIR, "..", "ansible", "group_vars", "all.yml")

# Mappings from (source_key) to (hcl_key)
# Source key can be from all.yml or from secrets (vault_*)
MAPPINGS = {
    "packer": {
        "proxmox_api_url": "proxmox_api_url",
        "proxmox_api_packer_token_id": "proxmox_api_token_id",
        "vault_packer_api_token_secret": "proxmox_api_token_secret",
        "proxmox_node": "proxmox_node",
        "proxmox_storage": "proxmox_storage",
        "proxmox_bridge": "proxmox_bridge",
        "network_gateway": "network_gateway",
        "build_ip_base": "build_ip_base",
        "build_ip_docker": "build_ip_docker",
        "build_ip_app": "build_ip_app",
        "packer_ssh_username": "ssh_username",
        "packer_cpu": "cpu",
        "packer_memory": "memory",
        "packer_disk_size": "disk_size",
        "template_cloud_image": "template_cloud_image",
        "template_ubuntu_base": "template_ubuntu_base",
        "template_ubuntu_docker": "template_ubuntu_docker",
        "template_dsv_app": "template_dsv_app",
        "template_iac_public_key": "template_iac_public_key",
        "vault_github_deploy_keys": "vault_github_deploy_keys",
    },
    "terraform": {
        "proxmox_api_url": "proxmox_api_url",
        "proxmox_api_terraform_token_id": "proxmox_api_token_id",
        "vault_proxmox_api_token_secret": "proxmox_api_token_secret",
        "proxmox_node": "proxmox_node",
        "proxmox_storage": "proxmox_storage",
        "proxmox_bridge": "proxmox_bridge",
        "template_dsv_app": "template_id",
        "app_vm_name": "vm_name",
        "app_vm_cpu": "vm_cpu",
        "app_vm_memory": "vm_memory",
        "app_vm_disk_size": "vm_disk_size",
        "app_vm_ip": "vm_ip",
    },
}


def load_yaml(path):
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Warning: {path} not found", file=sys.stderr)
        return {}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MAPPINGS:
        print(f"Usage: {sys.argv[0]} {{{'|'.join(MAPPINGS)}}}", file=sys.stderr)
        sys.exit(1)

    tool = sys.argv[1]
    mapping = MAPPINGS[tool]

    # Load non-secrets
    all_vars = load_yaml(ALL_VARS_PATH)

    # Load secrets from stdin
    secrets = yaml.safe_load(sys.stdin)
    if not secrets:
        print("Error: no data read from stdin", file=sys.stderr)
        sys.exit(1)

    # Combine data
    combined = {**all_vars, **secrets}

    for src_key, hcl_key in mapping.items():
        value = combined.get(src_key)
        if value is None:
            # Some values might be optional or handled elsewhere
            continue

        # Special handling for Proxmox API URL in Packer
        if tool == "packer" and src_key == "proxmox_api_url":
            if not value.endswith("/api2/json"):
                value = f"{value.rstrip('/')}/api2/json"

        # Format for HCL
        if isinstance(value, bool):
            out = str(value).lower()
        elif isinstance(value, (int, float)):
            out = str(value)
        else:
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            out = f'"{escaped}"'

        print(f"{hcl_key} = {out}")


if __name__ == "__main__":
    main()
