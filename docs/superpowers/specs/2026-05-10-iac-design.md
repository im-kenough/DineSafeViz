# v0.3.0 Infrastructure as Code — Design Spec

**Date:** 2026-05-10
**Purpose:** Introduce IaC for DineSafeViz using a layered golden image pipeline
(Packer + Ansible) with Terraform provisioning and Ansible deployment on a
Proxmox homelab.

## Summary

Build three layered Proxmox VM templates using Packer and Ansible, provision a
VM with Terraform, and deploy the DineSafeViz Docker Compose stack with an
Ansible playbook. This is a stepping stone toward a Kubernetes deployment
(v0.4.0+) — the base and docker image layers will be reused.

## Goals

1. **Reproducible infrastructure** — one command to go from nothing to a running app
2. **Layered golden images** — enterprise-standard bake-time pipeline
3. **Secrets hygiene** — nothing unencrypted in git, no hardcoded passwords
4. **Extensibility** — base/docker layers reusable for K8s nodes in v0.4.0+
5. **Documentation** — an engineer unfamiliar with this project can follow along

## Infrastructure Overview

### Proxmox Host

- **Host IP:** 10.0.20.21
- **Gateway/DNS:** 10.0.20.1
- **Bridge:** vmbr0
- **Storage:** local-lvm

### Target VM

| Property | Value |
|----------|-------|
| Hostname | yyz-app-dsv01 |
| IP | 10.0.20.80/24 |
| CPU | 2 cores |
| RAM | 4096 MB |
| Disk | 20 GB |
| OS | Ubuntu 24.04 LTS |
| Service account | adm-ubuntu |

## Technology Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Image building | Packer | Purpose-built for golden image pipelines; Proxmox plugin available |
| Configuration management | Ansible | Agentless, roles map cleanly to image layers, Vault built in |
| VM provisioning | Terraform (bpg/proxmox) | Declarative IaC, same provider as future K8s spec |
| Secrets management | Ansible Vault | Free, encrypted at rest, single source of truth |
| Container runtime | Docker CE + Compose plugin | Matches existing app architecture |
| Security hardening | Ansible role (homelab-grade) | SSH key-only, UFW, fail2ban, unattended-upgrades |

### Future migration path

- **K8s (v0.4.0+):** ubuntu-base and ubuntu-docker templates reused for K8s nodes
- **DISA STIG:** Aspirational hardening goal, can replace the base role's security tasks
- **Remote state:** Terraform state stays local for now; migrate to backend when multi-VM

## Proxmox Prerequisites

### Service Accounts

Two Proxmox API users with dedicated API tokens:

| Account | Purpose | Permissions |
|---------|---------|-------------|
| `svc-packer@pve` | Packer image builds | VM.Allocate, VM.Clone, VM.Config.*, VM.Audit, VM.Console, VM.Monitor, VM.PowerMgmt, Datastore.AllocateSpace, Datastore.Audit, Sys.Modify, SDN.Use |
| `svc-terraform@pve` | VM provisioning | VM.Allocate, VM.Clone, VM.Config.*, VM.Audit, VM.PowerMgmt, Datastore.AllocateSpace, Datastore.Audit, SDN.Use |

Both use API tokens (not passwords) — scoped, revocable, no account password required.

### Seed Cloud Image (Template 9000)

Download the Ubuntu 24.04 cloud image and import as Proxmox VM template 9000.
This is the raw upstream image that Packer builds on top of. One-time manual
setup documented in the install guide.

## Image Pipeline

Three layered Proxmox templates, each built by Packer using Ansible provisioners:

```
Ubuntu 24.04 cloud image (9000, manual import)
  └─ ubuntu-base (9100)         Packer + Ansible role: base
       └─ ubuntu-docker (9101)  Packer + Ansible role: docker
            └─ dsv-app (9102)   Packer + Ansible role: dsv-app
```

### Layer 1: ubuntu-base (Template 9100)

**Purpose:** Minimal, hardened Ubuntu server — reusable across all future VM types.

Ansible `base` role configures:

- **Service account:** `adm-ubuntu` with sudo, SSH key-only auth
- **Security hardening:**
  - Disable root login
  - Disable password authentication
  - UFW firewall (allow SSH only by default)
  - fail2ban (SSH jail)
  - unattended-upgrades (security patches only)
- **Common packages:** curl, wget, git, jq, htop, vim, ca-certificates, gnupg
- **System config:**
  - NTP via systemd-timesyncd
  - Timezone: America/Toronto
  - DNS: 10.0.20.1
- **Cleanup:** Truncate logs, clear apt cache, zero free space (smaller template)

**Rebuild cadence:** Monthly or after Ubuntu security advisories.

### Layer 2: ubuntu-docker (Template 9101)

**Purpose:** Docker-ready VM — base for any containerized workload.

Inherits from ubuntu-base (9100). Ansible `docker` role adds:

- **Docker CE** installed via the official apt repository method:
  1. Add Docker's official GPG key
  2. Add the Docker apt repository
  3. Install: docker-ce, docker-ce-cli, containerd.io, docker-buildx-plugin,
     docker-compose-plugin
- **Post-install:**
  - Add `adm-ubuntu` to the `docker` group (run Docker without sudo)
  - Enable Docker on boot: `systemctl enable docker.service`,
    `systemctl enable containerd.service`
  - Docker daemon config: log rotation, default address pool
- **UFW:** Allow ports 5000 (app) and 3000 (Grafana)
- **Smoke test:** `docker run hello-world`

**Rebuild cadence:** When Docker releases major versions or base image is updated.

### Layer 3: dsv-app (Template 9102)

**Purpose:** VM identity and access credentials — ready to receive a deployment.

Inherits from ubuntu-docker (9101). Ansible `dsv-app` role adds:

- **VM identity:** Hostname set to `yyz-app-dsv01`, static IP 10.0.20.80
- **GitHub deploy key:** Installed to `/home/adm-ubuntu/.ssh/deploy-key`
  (permissions 0600)
- **SSH config:** `~/.ssh/config` entry for github.com using the deploy key
- **App directory:** `/home/adm-ubuntu/app/` created, owned by `adm-ubuntu`

No repo clone, no `.env`, no Docker Compose. Those happen at deploy time.

**Rebuild cadence:** When base layers change or GitHub deploy key is rotated.

## Terraform — VM Provisioning

### What Terraform Does

1. Connects to Proxmox API using `svc-terraform@pve` API token
2. Clones template 9102 as a full VM
3. Sets VM resources (2 CPU, 4GB RAM, 20GB disk)
4. Starts the VM
5. Outputs the VM IP for Ansible to target

### What Terraform Does NOT Do

- No cloud-init network config (IP is baked into the image)
- No software installation
- No app deployment
- No secret management

### Provider

Uses the `bpg/proxmox` Terraform provider — consistent with the future K8s spec.

### State

Terraform state stored locally (terraform.tfstate, gitignored). Remote state
backends are overkill for a single homelab VM.

### Variables

All non-secret variables defined in `variables.tf` with defaults sourced from
`group_vars/all.yml`. Secret variables (API tokens) injected via
`terraform.tfvars` rendered from Ansible Vault at runtime.

## Ansible Deploy Playbook

After Terraform creates the VM, a separate Ansible playbook handles app
deployment. The playbook is idempotent — safe to re-run.

### Deploy Steps

1. **Wait for VM** — SSH connectivity check
2. **Clone or pull repo** — `git clone` if app dir doesn't exist, `git pull` if it does
3. **Template `.env`** — Render from Ansible Vault secrets, place in repo root
4. **Docker Compose up** — `docker compose up -d --build`
5. **Health check** — Wait for Flask app on port 5000

### Idempotency

| Scenario | Behavior |
|----------|----------|
| Fresh VM (post-Terraform) | Clones repo, creates .env, starts containers |
| Re-run (app running) | Pulls latest code, updates .env if changed, rebuilds/restarts |
| After teardown + reprovision | Same as fresh — full clone + deploy |

## Operations

### Command Matrix

| Command | What It Does | Tools |
|---------|-------------|-------|
| `make provision-vm` | Clone template 9102 → running VM | Terraform apply |
| `make deploy-app` | Clone repo, template .env, docker compose up | Ansible playbook |
| `make destroy-app` | docker compose down -v, remove repo (full wipe) | Ansible playbook |
| `make destroy-app-keep-data` | docker compose down, remove repo (keep volumes) | Ansible playbook |
| `make redeploy-app` | destroy-app → deploy-app | Ansible playbook |
| `make redeploy-app-keep-data` | destroy-app-keep-data → deploy-app | Ansible playbook |
| `make destroy-vm` | Delete VM entirely | Terraform destroy |

### Convenience Combos

| Command | Expands To |
|---------|-----------|
| `make up` | provision-vm → deploy-app |
| `make down` | destroy-app → destroy-vm |

## Secrets Management

### Principle: Single Source of Truth

Ansible Vault is the one place all secrets live. Both Terraform and Ansible
read from it:

```
infra/ansible/vault/secrets.yml  (Ansible Vault encrypted, committed)
  ├─ Ansible reads directly (--ask-vault-pass)
  └─ Terraform reads via auto-generated .tfvars
       └─ Makefile: decrypt vault → render terraform.tfvars → terraform apply
          (terraform.tfvars is gitignored, ephemeral)
```

### Vault Contents

```yaml
# Proxmox API tokens
vault_proxmox_api_token_id: svc-terraform@pve!terraform
vault_proxmox_api_token_secret: <token>
vault_packer_api_token_id: svc-packer@pve!packer
vault_packer_api_token_secret: <token>

# Database credentials
vault_db_user: dinesafe
vault_db_password: <password>
vault_db_name: dinesafe

# Analytics dashboard credentials
vault_analytics_admin_user: admin
vault_analytics_admin_password: <password>

# GitHub deploy key (private key)
vault_github_deploy_keys: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----
```

### What Lives Where

| File | Contents | In Git? |
|------|----------|---------|
| `ansible/vault/secrets.yml` | All secrets | Yes (Ansible Vault encrypted) |
| `ansible/group_vars/all.yml` | Non-secret config (IPs, specs, paths) | Yes (plaintext) |
| `terraform/terraform.tfvars` | Auto-generated from vault at runtime | No (gitignored) |
| `packer/variables.pkrvars.hcl` | Auto-generated from vault at runtime | No (gitignored) |
| `.env` (on VM) | Templated by Ansible at deploy time | No (never in repo) |

### Rules

1. Never commit unencrypted secrets to the repo
2. Never hardcode passwords in docker-compose.yml, .tf files, or playbooks
3. terraform.tfvars and .pkrvars.hcl are ephemeral — rendered at runtime, deleted after
4. .env files are templated onto the VM, never stored in the repo
5. Only Ansible Vault encrypted files may contain secret values in git

## Security Posture

### Current (v0.3.0)

- SSH key-only authentication (password auth disabled)
- Root login disabled
- UFW firewall (SSH, 5000, 3000 only)
- fail2ban (SSH brute-force protection)
- unattended-upgrades (security patches)
- Dedicated service accounts with minimal Proxmox privileges
- Ansible Vault for all secrets

### Future (aspirational)

- DISA STIG hardening via community Ansible role
- CIS benchmark compliance
- Audit logging
- AIDE file integrity monitoring

## File Structure

```
infra/
├── Makefile
├── scripts/
│   └── render-tfvars.py
├── packer/
│   ├── ubuntu-base.pkr.hcl
│   ├── ubuntu-docker.pkr.hcl
│   ├── dsv-app.pkr.hcl
│   └── variables.pkrvars.hcl.example
├── ansible/
│   ├── ansible.cfg
│   ├── inventory/
│   │   └── hosts.yml
│   ├── group_vars/
│   │   └── all.yml
│   ├── roles/
│   │   ├── base/
│   │   │   ├── tasks/main.yml
│   │   │   ├── handlers/main.yml
│   │   │   ├── templates/
│   │   │   └── files/
│   │   ├── docker/
│   │   │   ├── tasks/main.yml
│   │   │   └── handlers/main.yml
│   │   ├── dsv-app/
│   │   │   ├── tasks/main.yml
│   │   │   └── templates/
│   │   ├── deploy/
│   │   │   └── tasks/main.yml
│   │   └── destroy/
│   │       └── tasks/main.yml
│   ├── playbooks/
│   │   ├── packer-base.yml
│   │   ├── packer-docker.yml
│   │   ├── packer-dsv-app.yml
│   │   ├── deploy-dsv.yml
│   │   └── destroy-dsv.yml
│   └── vault/
│       └── secrets.yml

docs/
├── how-to/
│   ├── install-guide-iac.md       # NEW — first-time setup
│   └── deploy-guide-iac.md        # NEW — day-to-day operations
├── ref/
│   └── infra/
│       ├── iac-strategy.md        # NEW — IaC strategy overview
│       └── secrets-mgt.md         # UPDATED — Ansible Vault strategy
```

## .gitignore Additions

```gitignore
# Terraform
infra/terraform/.terraform/
infra/terraform/*.tfstate*
infra/terraform/.terraform.lock.hcl
infra/terraform/terraform.tfvars

# Packer
infra/packer/variables.pkrvars.hcl
infra/packer/.packer/

# VM .env (should never be in repo, but just in case)
.env
!.env.example
```

## Documentation Deliverables

### 1. `docs/ref/infra/iac-strategy.md`

IaC strategy document for a DevOps analyst or engineering manager audience.
Covers goals, architecture, technology choices, image pipeline, secrets
management, operations model, security posture, and K8s migration path.

### 2. `docs/how-to/install-guide-iac.md`

Step-by-step first-time setup:

1. Workstation prerequisites — install Packer, Terraform, Ansible
2. Proxmox setup — create service accounts, generate API tokens, assign permissions
3. Seed cloud image — download Ubuntu 24.04 cloud image, import as template 9000
4. Create Ansible Vault — populate all secrets
5. Build image layers — bake ubuntu-base, ubuntu-docker, dsv-app (in order)
6. Verify — confirm templates 9100, 9101, 9102 exist in Proxmox

### 3. `docs/how-to/deploy-guide-iac.md`

Day-to-day operations runbook:

- Provision + deploy (fresh start): `make up`
- Deploy app (VM exists): `make deploy-app`
- Redeploy app: `make redeploy-app` or `make redeploy-app-keep-data`
- Destroy app only: `make destroy-app` or `make destroy-app-keep-data`
- Destroy everything: `make down`
- Rebuild images: when and how to re-bake each layer
- Troubleshooting: common issues

### 4. `docs/ref/infra/secrets-mgt.md` (updated)

Add Ansible Vault strategy section:

- Single source of truth principle
- Vault contents (full key list)
- Terraform consumption via render-tfvars
- What's gitignored vs. encrypted vs. plaintext
- Rules for secrets handling
