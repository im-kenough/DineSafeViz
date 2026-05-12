# IT Security architecture

This document discusses the IT security architecture of DinsSafeViz

## Secrets Management

# Secrets Management

Make a draw.io diagram outlining the security flow

## Principles

1. **Single source of truth:** All secrets live in one Ansible Vault file
   (`infra/ansible/vault/secrets.yml`), encrypted at rest
2. **Nothing unencrypted in git:** `.tfvars`, `.pkrvars.hcl`, and `.env` files
   are gitignored and never committed
3. **No hardcoded passwords:** `docker-compose.yml`, `.tf` files, and Ansible
   playbooks reference variables, never literal secret values
4. **Ephemeral secret files:** Terraform and Packer variable files are rendered
   from the vault at runtime and deleted after use

## Architecture

```
Ansible Vault (encrypted, in git)
  │
  ├─ Ansible playbooks
  │   Read directly via --ask-vault-pass
  │
  ├─ Terraform
  │   Makefile decrypts vault → render-tfvars.py → terraform.tfvars (ephemeral)
  │
  ├─ Packer
  │   Makefile decrypts vault → render-pkrvars.py → variables.pkrvars.hcl (ephemeral)
  │
  └─ Application (.env on VM)
      Ansible deploy playbook templates .env from vault values
```

## Vault Contents

The vault file (`infra/ansible/vault/secrets.yml`) contains:

| Key | Description | Used by |
|-----|-------------|---------|
| `vault_proxmox_api_token_id` | Terraform Proxmox API token ID | Terraform |
| `vault_proxmox_api_token_secret` | Terraform Proxmox API token secret | Terraform |
| `vault_packer_api_token_id` | Packer Proxmox API token ID | Packer |
| `vault_packer_api_token_secret` | Packer Proxmox API token secret | Packer |
| `vault_db_user` | PostgreSQL username | Ansible deploy (.env) |
| `vault_db_password` | PostgreSQL password | Ansible deploy (.env) |
| `vault_db_name` | PostgreSQL database name | Ansible deploy (.env) |
| `vault_analytics_admin_user` | Grafana admin username | Ansible deploy (.env) |
| `vault_analytics_admin_password` | Grafana admin password | Ansible deploy (.env) |
| `vault_github_app_key` | GitHub App private key (RSA) | Packer dsv-app build |

## What Lives Where

| File | Contents | In Git? |
|------|----------|---------|
| `infra/ansible/vault/secrets.yml` | All secrets | Yes (encrypted) |
| `infra/ansible/group_vars/all.yml` | Non-secret config | Yes (plaintext) |
| `infra/terraform/terraform.tfvars` | Rendered from vault | No (gitignored) |
| `infra/packer/variables.pkrvars.hcl` | Rendered from vault | No (gitignored) |
| `.env` (on VM at deploy time) | Templated from vault | No (never in repo) |
| `.env.example` (in repo root) | Placeholder values | Yes (no real secrets) |

## Vault Operations

### View secrets

```bash
cd infra/ansible
ansible-vault view vault/secrets.yml --ask-vault-pass
```

### Edit secrets

```bash
cd infra/ansible
ansible-vault edit vault/secrets.yml --ask-vault-pass
```

### Change vault password

```bash
cd infra/ansible
ansible-vault rekey vault/secrets.yml --ask-vault-pass
```

## Rules

- **Never** commit unencrypted secrets to the repository
- **Never** hardcode passwords in `docker-compose.yml`, `.tf` files, or
  playbooks
- **Never** store `.tfvars` or `.pkrvars.hcl` files with real values in git
- **Always** use `--ask-vault-pass` (or a vault password file) when running
  Ansible or Make targets
- `.env` files exist only on the target VM, templated at deploy time


## Repository Security

Security measures implemented in the repo

Dependabot enabled to scan for outdated software


## Shift left

IDE configurations:
- a
- b
- c