# IT security architecture

This document describes the security architecture of DineSafeViz,
covering secrets management, VM hardening, network controls, service
accounts, and repository-level safeguards.

## Principles

1. **Single source of truth:** All secrets live in one Ansible Vault
   file (`infra/ansible/vault/secrets.yml`), encrypted at rest.
2. **Nothing unencrypted in git:** `.tfvars`, `.pkrvars.hcl`, and
   `.env` files are gitignored and never committed.
3. **No hardcoded passwords:** `docker-compose.yml`, `.tf` files, and
   Ansible playbooks reference variables, never literal secret values.
4. **Ephemeral secret files:** Terraform and Packer variable files are
   rendered from the vault at runtime and deleted after use.
5. **Hardened by default:** Security controls (SSH hardening, firewall,
   intrusion prevention, automatic patching) are baked into the VM
   image at build time, not applied post-deploy.

## Secrets management

Ansible Vault is the single store for all credentials. No other secret
store is used. The Makefile orchestrates a decrypt-render-cleanup
pipeline so plaintext secrets exist only in memory or in short-lived
files that are deleted immediately after use.

### Architecture

```
Ansible Vault (encrypted, in git)
  │
  ├─ Ansible playbooks
  │   Read directly via --ask-vault-pass
  │
  ├─ Terraform
  │   Makefile decrypts vault → render-tfvars.py → terraform.tfvars
  │   (ephemeral, deleted after terraform apply)
  │
  ├─ Packer
  │   Makefile decrypts vault → render-pkrvars.py → variables.pkrvars.hcl
  │   (ephemeral, deleted after packer build)
  │
  └─ Application (.env on VM)
      Ansible deploy playbook templates .env from vault values
      (mode 0600, never committed to git)
```

### Vault contents

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
| `vault_github_deploy_keys` | GitHub deploy key (private key) | Packer dsv-app build |

### What lives where

| File | Contents | In git? |
|------|----------|---------|
| `infra/ansible/vault/secrets.yml` | All secrets | Yes (encrypted) |
| `infra/ansible/group_vars/all.yml` | Non-secret config | Yes (plaintext) |
| `infra/terraform/terraform.tfvars` | Rendered from vault | No (gitignored) |
| `infra/packer/variables.pkrvars.hcl` | Rendered from vault | No (gitignored) |
| `.env` (on VM at deploy time) | Templated from vault | No (never in repo) |

## VM hardening

VM hardening is applied at image build time via the Ansible `base`
role (`infra/ansible/roles/base/`). Every VM cloned from the base
template inherits these controls automatically.

### SSH hardening

A hardened `sshd_config` is deployed
(`infra/ansible/roles/base/templates/sshd_config.j2`):

| Setting | Value | Purpose |
|---------|-------|---------|
| `PermitRootLogin` | `no` | Prevents direct root access |
| `PasswordAuthentication` | `no` | Key-only authentication |
| `PubkeyAuthentication` | `yes` | SSH keys required |
| `MaxAuthTries` | `3` | Limits brute-force attempts |
| `X11Forwarding` | `no` | Disables unnecessary feature |
| `ClientAliveInterval` | `300` | Drops idle sessions after 5 min |
| `ClientAliveCountMax` | `2` | Two missed keepalives before disconnect |

### Firewall (UFW)

UFW is configured with a default-deny-incoming policy. Only the
following ports are explicitly opened:

| Port | Protocol | Service |
|------|----------|---------|
| 22 | TCP | SSH |
| 5000 | TCP | Flask web app |
| 3000 | TCP | Grafana (admin access) |

### Intrusion prevention (fail2ban)

fail2ban monitors `/var/log/auth.log` for SSH brute-force attempts
(`infra/ansible/roles/base/files/jail.local`):

| Setting | Value |
|---------|-------|
| `maxretry` | 5 |
| `bantime` | 3600 s (1 hour) |
| `findtime` | 600 s (10 min) |

### Automatic security patching

`unattended-upgrades` is enabled to apply security patches daily.
The configuration updates package lists daily, runs unattended
upgrades daily, and autocleans the apt cache weekly.

## Service accounts

The following service accounts and credentials are used, grouped by
function.

### VM automation

| Account | Purpose | Auth method |
|---------|---------|-------------|
| `adm-ubuntu` | Ansible and app management on the VM | SSH key (passwordless sudo) |

The `adm-ubuntu` account is created by the `base` role. It has
passwordless sudo (required for Ansible automation) and SSH key-only
access. The authorized keys are copied from the build user during
Packer image creation.

### Proxmox API

Two dedicated Proxmox service accounts with separate API tokens,
following the principle of least privilege:

| Account | Role | Token (vault key) | Used by |
|---------|------|--------------------|---------|
| `svc-packer@pve` | `Packer` | `vault_packer_api_token_id/secret` | Packer |
| `svc-terraform@pve` | `Terraform` | `vault_proxmox_api_token_id/secret` | Terraform |

Each account uses an API token (`--privsep 0`) rather than a
password. The Proxmox roles are custom-created with minimal
permissions:

- **Packer role:** VM.Allocate, VM.Clone, VM.Config.*, VM.Audit,
  VM.Console, VM.Monitor, VM.PowerMgmt, Datastore.AllocateSpace,
  Datastore.Audit, Sys.Modify, SDN.Use
- **Terraform role:** VM.Allocate, VM.Clone, VM.Config.*, VM.Audit,
  VM.PowerMgmt, Datastore.AllocateSpace, Datastore.Audit, SDN.Use

Neither account has full administrator access. If a token is
compromised, the blast radius is limited to VM operations — no access
to storage content, networking configuration, or other Proxmox
nodes.

### GitHub access

| Credential | Purpose | Used by |
|------------|---------|---------|
| `vault_github_deploy_keys` | Clone the repo to the VM via SSH | Packer dsv-app build, Ansible deploy |

A read-only GitHub deploy key (ed25519) is used instead of a personal
access token. Deploy keys are scoped to a single repository and cannot
push, manage settings, or access other repos. The private key is
installed to `/home/adm-ubuntu/.ssh/deploy-key` (mode `0600`) during
the Packer dsv-app build. The SSH config on the VM
(`infra/ansible/roles/dsv-app/templates/ssh_config.j2`) pins the
identity file and sets `IdentitiesOnly yes` to prevent key leakage.

### Application credentials

| Credential | Purpose | Scope |
|------------|---------|-------|
| `vault_db_user` / `vault_db_password` | PostgreSQL access | Docker internal network only |
| `vault_analytics_admin_user` / `vault_analytics_admin_password` | Grafana admin | Grafana web UI |

These are injected into the `.env` file on the VM at deploy time
(mode `0600`) and consumed by Docker Compose as environment variables.
The PostgreSQL instance isn't exposed outside the Docker network.

## Repository security

Security measures implemented in the GitHub repository.

### Dependabot

Dependabot (`.github/dependabot.yml`) is enabled with weekly scans
across four ecosystems:

| Ecosystem | Directory | What it covers |
|-----------|-----------|----------------|
| `pip` | `/src/dsv-app` | Python dependencies |
| `docker` | `/src/dsv-app` | Flask app base image |
| `docker` | `/src/dsv-db` | Database init base image |
| `github-actions` | `/` | Workflow action versions |

### Gitignore protections

The `.gitignore` prevents accidental commits of sensitive files:

- `.env` and `.envrc` — runtime secrets
- `infra/terraform/terraform.tfvars` — rendered Terraform secrets
- `infra/packer/variables.pkrvars.hcl` — rendered Packer secrets
- `infra/terraform/*.tfstate*` — Terraform state (contains resource
  IDs and metadata)
- `.streamlit/secrets.toml` — Streamlit secrets

## Container security

The application containers follow security best practices where
possible.

### Image selection

Both application Dockerfiles use `python:3.14-slim` as the base
image, which provides a minimal attack surface compared to full
images.

### Network isolation

The Docker Compose stack uses an internal bridge network. Only ports
5000 (Flask) and 3000 (Grafana) are published to the host. PostgreSQL
is only accessible from other containers on the internal network and
isn't exposed to the host or the broader network.

### Log management

Docker daemon logging is configured via
`infra/ansible/roles/docker/templates/daemon.json.j2` to prevent
unbounded disk usage:

- Max log size: `10m` per container
- Max log files: `3` per container

## Shift-left practices

IDE and local development configurations that catch issues early.

No IDE-specific configurations (`.editorconfig`, `.vscode/`,
`.pre-commit-config.yaml`) are currently in the repository. This is
an area for future improvement. Potential additions include:

- Pre-commit hooks for secret scanning (for example, `detect-secrets`
  or `gitleaks`)
- Linting and formatting enforcement
- Editor configuration for consistent code style
