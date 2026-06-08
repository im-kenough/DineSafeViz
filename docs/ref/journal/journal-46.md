# Journal 46 — v0.3.0 IaC Design (Packer + Ansible + Terraform)

## 2026-05-10 14:00

**Session goal:** Design the IaC strategy for v0.3.0 — layered golden image
pipeline (Packer + Ansible) with Terraform provisioning and Ansible deployment
for a single Docker Compose VM on Proxmox.

### Context

- Existing K8s design spec (`docs/superpowers/specs/2026-05-01-homelab-k8s-design.md`) is
  shelved as v0.4.0+. This v0.3.0 effort is a stepping stone — the base and docker image
  layers will be reused when K8s comes.
- Current deploy is manual: SSH into Proxmox VM, clone repo, docker compose up.

### Key decisions made during brainstorming

1. **Approach A (Fully Baked Images)** chosen over lighter alternatives — three Packer
   templates (base → docker → app), each using Ansible provisioners.
2. **Packer + Ansible** for image building (enterprise golden image pattern), not cloud-init only.
3. **Homelab-hardened security** (SSH key-only, UFW, fail2ban, unattended-upgrades).
   DISA STIG is aspirational future goal.
4. **Ansible Vault** as single source of truth for all secrets. Terraform consumes
   secrets via a render-tfvars.py script at runtime.
5. **Layer 3 (dsv-app)** only sets VM identity (hostname, IP) and installs GitHub App key.
   Repo cloning happens in deploy playbook, not baked in.
6. **Docker installed** via official apt repository method per Docker docs.
7. **Separate Proxmox service accounts** for Packer (`svc-packer@pve`) and Terraform
   (`svc-terraform@pve`) with minimal privileges.
8. **Operations:** provision-vm, deploy-app, destroy-app (with keep-data variant),
   redeploy-app, destroy-vm — all via Makefile targets.
9. **Documentation:** iac-strategy.md, install-guide-iac.md, deploy-guide-iac.md,
   updated secrets-mgt.md.

### Proxmox details

- Host: 10.0.20.21, bridge vmbr0, gateway/DNS 10.0.20.1, storage local-lvm
- DSV VM: yyz-app-dsv01, IP 10.0.20.80, 2 CPU / 4GB RAM / 20GB disk
- Template IDs: 9000 (cloud image), 9100 (base), 9101 (docker), 9102 (dsv-app)

## 2026-05-10 14:30

Writing design spec to `docs/superpowers/specs/2026-05-10-iac-design.md`.

## 2026-05-10 15:00

Wrote implementation plan to `docs/superpowers/plans/2026-05-10-iac.md`.
19 tasks covering: directory scaffold, Ansible config/inventory/group_vars,
3 Ansible roles (base, docker, dsv-app), 3 Packer templates, deploy/destroy
roles and playbooks, Terraform config, render-tfvars/pkrvars scripts,
Makefile, Ansible Vault setup, and 4 documentation files.

Self-review found one bug: DNS resolver directory creation was ordered after
the file copy that writes into it (base role). Fixed by swapping the task
order.

## 2026-05-10 16:00

Executed all 19 tasks of the implementation plan via Subagent-Driven Development.

### Commits on `feat/iac-v0.3.0` (18 commits, 32 files):

| Commit | Task | Description |
|--------|------|-------------|
| `4d0b3f0` | 1 | Scaffold directory structure + .gitignore |
| `a7f270e` | 2 | Ansible config, inventory, group_vars |
| `5e1a744` | 3 | Base role — OS hardening, SSH, UFW, fail2ban |
| `2b169f8` | 4 | Docker role — Docker CE via official apt repo |
| `0c6eb61` | 5 | dsv-app role — VM identity + GitHub App key |
| `ed5b710` | 6 | Packer template — ubuntu-base (Layer 1) |
| `c3a632d` | 7 | Packer template — ubuntu-docker (Layer 2) |
| `775798b` | 8 | Packer template — dsv-app (Layer 3) + vars example |
| `753bd7a` | 9 | Deploy role — clone repo, template .env, compose up |
| `f28667e` | 10 | Destroy role — tear down with keep-data option |
| `790a997` | 11 | Terraform config for Proxmox VM provisioning |
| `6f9e387` | 12 | render-tfvars.py — bridges Vault to Terraform |
| `e892948` | 13 | Makefile + render-pkrvars.py — orchestrate all ops |
| `11e2861` | 15 | IaC strategy document |
| `a23c794` | 16 | Install guide — first-time setup |
| `210c85d` | 17 | Deploy guide — day-to-day operations |
| `46c5457` | 18 | Secrets management — Ansible Vault strategy |

Task 14 (Ansible Vault setup) skipped — requires interactive `ansible-vault create`.

### Final validation results:

- All 32 infra files present and accounted for
- Both render scripts produce correct HCL output from YAML input
- .gitignore covers terraform.tfvars, .terraform/, variables.pkrvars.hcl
- Makefile `help` target lists all 14 targets correctly
- Ansible and Terraform not installed on this machine — syntax checks skipped
