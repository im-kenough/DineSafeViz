# Journal 63 — Update arch-security.md

## 2026-05-12 — Session start

Goal: Read the repo's security-related files and update
`docs/ref/arch/arch-security.md` to accurately reflect the current state.

### 2026-05-12 10:00 — Initial investigation

Reading current arch-security.md and scanning repo for security-relevant
configs: .gitignore, Ansible roles (base, docker, deploy), Packer templates,
GitHub config, IDE settings.

Files read:
- `.gitignore` — confirmed gitignore covers tfvars, pkrvars, .env, tfstate
- `infra/ansible/roles/base/tasks/main.yml` — SSH hardening, UFW, fail2ban,
  unattended-upgrades
- `infra/ansible/roles/base/templates/sshd_config.j2` — key-only, no root,
  MaxAuthTries 3
- `infra/ansible/roles/base/files/jail.local` — fail2ban: 5 retries, 1h ban
- `infra/ansible/group_vars/all.yml` — service account is `adm-ubuntu`
- `infra/ansible/roles/docker/tasks/main.yml` — UFW opens 5000, 3000
- `infra/ansible/roles/docker/templates/daemon.json.j2` — log rotation 10m/3
- `infra/ansible/roles/dsv-app/tasks/main.yml` — GitHub App key, SSH config
- `infra/ansible/roles/dsv-app/templates/ssh_config.j2` — IdentitiesOnly yes
- `infra/ansible/roles/deploy/tasks/main.yml` — .env mode 0600
- `infra/ansible/roles/deploy/templates/env.j2` — DB + Grafana creds
- `.github/dependabot.yml` — pip, docker x2, github-actions, weekly
- `infra/Makefile` — decrypt-render-cleanup pipeline
- `infra/scripts/render-tfvars.py`, `render-pkrvars.py` — ephemeral renderers
- `docker-compose.yml` — Postgres not exposed, env var injection
- `src/dsv-app/Dockerfile`, `src/dsv-db/Dockerfile` — python:3.14-slim
- `infra/terraform/main.tf` — Proxmox provider with API token
- `infra/packer/ubuntu-base.pkr.hcl` — sensitive=true on token secret
- No `.vscode/`, `.editorconfig`, `.pre-commit-config.yaml` found

### 2026-05-12 10:15 — Rewrote arch-security.md

Replaced the stub document with a comprehensive version covering:
- Principles (added "hardened by default" as 5th principle)
- Secrets management (architecture diagram, vault contents, file map)
- VM hardening (SSH, UFW, fail2ban, unattended-upgrades) — all with
  specific settings from the actual config files
- Service accounts grouped by function (VM automation, Proxmox API,
  GitHub access, application credentials)
- Repository security (Dependabot ecosystems, gitignore protections)
- Container security (slim images, network isolation, log management)
- Shift-left (documented current gap: no IDE configs or pre-commit hooks)
