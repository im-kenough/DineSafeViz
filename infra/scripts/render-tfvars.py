#!/usr/bin/env python3
"""Read decrypted Ansible Vault YAML from stdin, write terraform.tfvars to stdout.

Usage:
    ansible-vault view ansible/vault/secrets.yml --ask-vault-pass | python3 scripts/render-tfvars.py
"""

import sys
import yaml


# Map vault keys to Terraform variable names
VAULT_TO_TF = {
    "vault_proxmox_api_token_id": "proxmox_api_token_id",
    "vault_proxmox_api_token_secret": "proxmox_api_token_secret",
    "vault_proxmox_node": "proxmox_node",
}


def main():
    data = yaml.safe_load(sys.stdin)
    if not data:
        print("Error: no data read from stdin", file=sys.stderr)
        sys.exit(1)

    for vault_key, tf_key in VAULT_TO_TF.items():
        value = data.get(vault_key)
        if value is None:
            print(f"Warning: '{vault_key}' not found in vault", file=sys.stderr)
            continue
        # Escape backslashes and quotes for HCL string
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        print(f'{tf_key} = "{escaped}"')


if __name__ == "__main__":
    main()
