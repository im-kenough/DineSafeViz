# IT security architecture

This document describes the security architecture of DineSafeViz,
covering secrets management, VM hardening, network controls, service
accounts, and repository-level safeguards.

## Design principles

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

Ansible Vault is the single store for all credentials. The Makefile orchestrates a decrypt-render-cleanup pipeline so plaintext secrets exist only in memory or in short-lived files that are deleted immediately after use.

For rotation steps, see [rotate secrets](../../how-to/6-rotate-secrets.md).

### Secrets and variable locations

| File | Contents | In git? |
|------|----------|---------|
| `infra/ansible/vault/secrets.yml` | All IaC and application secrets. Encrypted with Ansible Vault. | Yes (encrypted) |
| `infra/ansible/group_vars/all.yml` | Contains all IaC and app configuration variables | Yes (plaintext) |
| `infra/terraform/terraform.tfvars` | Rendered from vault during deployment | No (gitignored) |
| `infra/packer/variables.pkrvars.hcl` | Rendered from vault during deployment  | No (gitignored) |
| `.env` (on VM at deploy time) | Templated from vault during deployment | No (never in repo) |

### Secret inventory (Ansible Vault)

The Ansible Vault encrypted file (`infra/ansible/vault/secrets.yml`) contains
every secret for IaC and the app. This is the complete list, keyed by the exact
name that the code consumes. The
`infra/ansible/vault/example-secrets.yml` template documents the same keys.

| Vault key | What it is used for | Consumed by |
|-----------|---------------------|-------------|
| `vault_proxmox_api_token_secret` | Authenticates Terraform to the Proxmox API for VM provisioning. | `render-vars.py terraform` → `terraform.tfvars` |
| `vault_packer_api_token_secret` | Authenticates Packer to the Proxmox API for image builds. | `render-vars.py packer` → `variables.pkrvars.hcl` |
| `vault_db_password` | Password for the PostgreSQL superuser role (`dinesafe`) that creates the schema and ingests data. | `env.j2` → `DSV_DB_PASSWORD` |
| `vault_db_app_password` | Password for the SELECT-only PostgreSQL role (`dinesafe_app`); optional, defaults to `dinesafe_app`. | `env.j2` → `DSV_DB_APP_PASSWORD` |
| `vault_analytics_admin_password` | Password for the Grafana admin user (`admin`). | `env.j2` → `DSV_ANALYTICS_ADMIN_PASSWORD` |
| `vault_github_deploy_keys` | Private half of the read-only GitHub deploy key that clones the repo onto the VM. | `render-vars.py packer` and the Packer `dsv-app` build |

> [!NOTE]
> The Proxmox token IDs, database usernames, and database name are identifiers,
> not secrets. They live in plaintext in `group_vars/all.yml` (see the next
> section), not in the vault.

### Non-secret identifiers (group_vars/all.yml)

These name accounts and resources but hold no secret value, so they live in
plaintext `infra/ansible/group_vars/all.yml`.

| Identifier | Value | What it is used for |
|------------|-------|---------------------|
| `proxmox_api_terraform_token_id` | `svc-terraform@pve!terraform` | Names the Proxmox API token that Terraform authenticates with. |
| `proxmox_api_packer_token_id` | `svc-packer@pve!packer` | Names the Proxmox API token that Packer authenticates with. |
| `app_analytics_db_user` | `dinesafe` | PostgreSQL superuser and database owner role name. |
| `app_analytics_db_app_user` | `dinesafe_app` | SELECT-only PostgreSQL role name used by the app and Grafana. |
| `app_analytics_db_name` | `dinesafe` | Application database name. |
| `app_analytics_admin_user` | `admin` | Grafana admin username. |
| `service_account` / `packer_ssh_username` | `adm-ubuntu` | Linux account on the VM for Ansible, app management, and Packer builds. |
| `template_iac_public_key` | `ssh-ed25519 … iac` | Public IaC SSH key baked into every template for provisioning access. |


---

## Service accounts

The following service accounts and credentials are used, grouped by
function.

### VM automation

| Account or key | What it is used for | Auth method |
|----------------|---------------------|-------------|
| `adm-ubuntu` | Linux account for Ansible automation and app management on the build and app VMs. | SSH key, passwordless sudo |
| `root@pve` | Proxmox host root, used manually during template creation for `pveum` and `qm` commands. | SSH (manual) |
| `iac` SSH key (`~/.ssh/iac`) | Workstation key for all IaC SSH access to the build and app VMs; its public half is baked into every template. | ed25519 key pair |

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
compromised, the affected area is limited to VM operations — no access
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

| Credential | What it is used for | Scope |
|------------|---------------------|-------|
| `vault_db_password` | Superuser password for the `dinesafe` role. | Docker internal network only |
| `vault_db_app_password` | Password for the SELECT-only `dinesafe_app` role. | Docker internal network only |
| `vault_analytics_admin_password` | Grafana admin password for the `admin` user. | Grafana web UI |

These are injected into the `.env` file on the VM at deploy time
(mode `0600`) and consumed by Docker Compose as environment variables.
The PostgreSQL instance isn't exposed outside the Docker network.

### PostgreSQL roles

Defined in `src/dsv-db/init.sql`.

| Role | What it is used for |
|------|---------------------|
| `dinesafe` | Bootstrap superuser (`POSTGRES_USER`) that creates the schema and runs data ingestion through `dsv-init-db`. |
| `dinesafe_app` | SELECT-only role that the Flask app and Grafana use to read inspection data. |
| `dinesafe_migrator` | DDL-capable role defined for future schema migrations; not yet used at runtime. |

### Grafana identities

| Identity | What it is used for |
|----------|---------------------|
| `admin` | Grafana administrator account (username from `app_analytics_admin_user`, password from `vault_analytics_admin_password`). |
| Anonymous viewer | Anonymous access is enabled with the Viewer org role so the embedded dashboard renders without a login. |

---


## Planned identities (v0.4.0 AKS)

The AKS rearchitecture introduces Azure managed identities and a Key Vault
secret. The [Azure component inventory](../azure-component-inventory.md) is the
authoritative list. This table summarizes the prod identities. The staging
environment mirrors them with `-stg-` names.

| Identity | What it is used for |
|----------|---------------------|
| `id-gha-dsv-shared-eus2` | GitHub Actions identity (OIDC) for the image-build and shared-infrastructure workflows. |
| `id-gha-dsv-prod-eus2` | GitHub Actions identity (OIDC) for the prod Terraform and app-deploy workflows. |
| `id-aks-controlplane-prod-eus2` | AKS control-plane identity that pulls images from ACR and manages the VNet. |
| `id-aks-cnpg-prod-eus2` | Workload Identity for CloudNativePG to write WAL files and backups to Azure Blob. |
| `id-aks-certmgr-prod-eus2` | Workload Identity for the cert-manager DNS-01 solver on the Azure DNS zone. |
| `id-aks-kvcsi-prod-eus2` | Workload Identity for the Key Vault CSI driver to read secrets. |
| `analytics-admin-password` (Key Vault secret) | Grafana admin credential stored in Azure Key Vault. |

## VM hardening

The app VM runs an Ubuntu OS with basic hardening.

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
| 8080 | TCP | nginx reverse proxy (web app and analytics) |
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

---

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
8080 (nginx) and 3000 (Grafana) are published to the host. The Flask
app (`dsv-app`) listens on internal port 8000 and is not published.
PostgreSQL is only accessible from other containers on the internal
network and isn't exposed to the host or the broader network.

### Log management

Docker daemon logging is configured via
`infra/ansible/roles/docker/templates/daemon.json.j2` to prevent
unbounded disk usage:

- Max log size: `10m` per container
- Max log files: `3` per container

## Shift-left practices

IDE and local development configurations that catch issues early.

Coming Soon (™️)

- Pre-commit hooks for secret scanning (for example, `detect-secrets`
  or `gitleaks`)
- Linting and formatting enforcement
- Editor configuration for consistent code style
