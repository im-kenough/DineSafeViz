#!/usr/bin/env python3
"""Read decrypted Ansible Vault YAML from stdin, write HCL variable assignments to stdout.

Usage:
    ansible-vault view vault/secrets.yml --ask-vault-pass | python3 scripts/render-vars.py packer
    ansible-vault view vault/secrets.yml --ask-vault-pass | python3 scripts/render-vars.py terraform
"""

import sys
import yaml

# Separate vault keys per tool — Packer and Terraform use distinct API tokens.
MAPPINGS = {
    "packer": {
        "vault_packer_api_token_id": "proxmox_api_token_id",
        "vault_packer_api_token_secret": "proxmox_api_token_secret",
        "vault_proxmox_node": "proxmox_node",
    },
    "terraform": {
        "vault_proxmox_api_token_id": "proxmox_api_token_id",
        "vault_proxmox_api_token_secret": "proxmox_api_token_secret",
        "vault_proxmox_node": "proxmox_node",
    },
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MAPPINGS:
        print(f"Usage: {sys.argv[0]} {{{'|'.join(MAPPINGS)}}}", file=sys.stderr)
        sys.exit(1)

    mapping = MAPPINGS[sys.argv[1]]
    data = yaml.safe_load(sys.stdin)
    if not data:
        print("Error: no data read from stdin", file=sys.stderr)
        sys.exit(1)

    for vault_key, hcl_key in mapping.items():
        value = data.get(vault_key)
        if value is None:
            print(f"Warning: '{vault_key}' not found in vault", file=sys.stderr)
            continue
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        print(f'{hcl_key} = "{escaped}"')


if __name__ == "__main__":
    main()
