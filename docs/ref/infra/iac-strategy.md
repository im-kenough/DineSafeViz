# Infrastructure as Code Strategy

## Purpose

This document describes the IaC strategy for DineSafeViz. It is written for a
DevOps analyst or engineering manager who needs to understand how
infrastructure is provisioned, configured, and deployed.

## Goals

1. **Reproducible infrastructure** — `make up` goes from nothing to a running
   application
2. **Layered golden images** — enterprise-standard bake-time pipeline using
   Packer and Ansible
3. **Secrets hygiene** — no unencrypted secrets in git, no hardcoded
   passwords, single source of truth in Ansible Vault
4. **Extensibility** — base and docker image layers are reusable for
   Kubernetes nodes (planned v0.4.0+)

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Image Pipeline (Packer + Ansible)      │
│                                                          │
│  Ubuntu 24.04 cloud image (template 9000)                │
│    └─ ubuntu-base (9100)     OS hardening, common pkgs   │
│         └─ ubuntu-docker (9101)  Docker CE + Compose     │
│              └─ dsv-app (9102)   VM identity + GH key    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                    VM Provisioning (Terraform)            │
│                                                          │
│  Clone template 9102 → running VM (yyz-app-dsv01)        │
│  2 CPU / 4 GB RAM / 20 GB disk / IP 10.0.20.80           │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                    App Deployment (Ansible)               │
│                                                          │
│  SSH into VM → git clone → template .env → docker        │
│  compose up → health check                               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Technology Choices

| Component | Tool | Why |
|-----------|------|-----|
| Image building | Packer | Purpose-built for golden images; has a Proxmox plugin |
| Configuration | Ansible | Agentless, roles map to image layers, Vault built in |
| Provisioning | Terraform (bpg/proxmox) | Declarative IaC, same provider planned for K8s |
| Secrets | Ansible Vault | Free, encrypts at rest, committed safely to git |
| Containers | Docker CE + Compose | Matches the existing application architecture |

## Image Pipeline

### Why Layered Images?

Each layer adds one concern. When Docker releases a new version, only the
docker layer (and its children) need rebuilding — the base layer stays
unchanged. When K8s comes later, ubuntu-base and ubuntu-docker are reused
directly.

### Layer Details

**Layer 1: ubuntu-base (template 9100)**

Minimal hardened Ubuntu 24.04 server. Reusable across all VM types.

- Service account (`adm-ubuntu`) with SSH key-only auth
- Security: UFW firewall, fail2ban, disabled root login, disabled password
  auth, unattended security upgrades
- Common packages: curl, wget, git, jq, htop, vim
- System: NTP, timezone (America/Toronto), DNS (10.0.20.1)

Rebuild cadence: monthly or after Ubuntu security advisories.

**Layer 2: ubuntu-docker (template 9101)**

Docker-ready VM. Base for any containerized workload.

- Docker CE installed via the official apt repository method
- `adm-ubuntu` can run Docker without sudo
- Docker and containerd enabled on boot via systemd
- Docker daemon configured (log rotation)
- UFW: ports 5000 and 3000 open

Rebuild cadence: on Docker major releases or base layer updates.

**Layer 3: dsv-app (template 9102)**

Application identity and credentials.

- Hostname: yyz-app-dsv01
- Static IP: 10.0.20.80
- GitHub App private key for repo cloning
- App directory created (`/home/adm-ubuntu/app/`)

Rebuild cadence: on base layer changes or GitHub App key rotation.

## Secrets Management

See [Secrets Management](secrets-mgt.md) for the full strategy.

Summary: Ansible Vault is the single source of truth. Terraform and Packer
consume secrets via helper scripts that render ephemeral `.tfvars`/`.pkrvars.hcl`
files at runtime. These files are gitignored and deleted after use.

## Operations

All operations run from `infra/` via Makefile targets:

| Command | Description |
|---------|-------------|
| `make bake-all` | Build all three image layers (base → docker → app) |
| `make provision-vm` | Create VM from dsv-app template (Terraform) |
| `make deploy-app` | Clone repo, template .env, docker compose up (Ansible) |
| `make destroy-app` | Stop containers, remove volumes, remove repo |
| `make destroy-app-keep-data` | Stop containers, keep volumes |
| `make redeploy-app` | destroy-app + deploy-app |
| `make redeploy-app-keep-data` | destroy-app-keep-data + deploy-app |
| `make destroy-vm` | Delete the VM (Terraform destroy) |
| `make up` | provision-vm + deploy-app |
| `make down` | destroy-app + destroy-vm |

## Security

### Current (v0.3.0)

- SSH key-only authentication, root login disabled
- UFW firewall: only SSH (22), app (5000), Grafana (3000)
- fail2ban: SSH brute-force protection
- Unattended security upgrades
- Dedicated Proxmox service accounts with minimal privileges
- All secrets encrypted with Ansible Vault

### Aspirational

- DISA STIG hardening
- CIS benchmark compliance
- Audit logging, AIDE file integrity monitoring

## Future: Kubernetes (v0.4.0+)

The base and docker image layers are designed for reuse:

- `ubuntu-base` → K8s node base (same hardening)
- `ubuntu-docker` → becomes `ubuntu-k8s` (swap Docker for containerd +
  kubeadm)
- A separate K8s-specific design spec covers the cluster architecture

## File Layout

```
infra/
├── Makefile                 Orchestrates all operations
├── scripts/
│   ├── render-tfvars.py     Vault → terraform.tfvars
│   └── render-pkrvars.py    Vault → packer .pkrvars.hcl
├── packer/                  Image build templates (Layers 1-3)
├── terraform/               VM provisioning
└── ansible/
    ├── roles/               Configuration roles per layer + deploy/destroy
    ├── playbooks/           Packer playbooks + deploy/destroy playbooks
    ├── group_vars/all.yml   Centralized non-secret config
    └── vault/secrets.yml    Encrypted secrets (single source of truth)
```
