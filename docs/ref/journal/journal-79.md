# Journal 79 — Simplify IAC Code in infra/

## 2026-05-19 — Session Start

### Goal
Simplify the Infrastructure as Code in `infra/`, centralize variables, and improve efficiency.

### Context
- Branch: `feat/iac-v0.3.0-deploy`
- All 38 files in `infra/` are new (1,677 additions vs main)
- Stack: Packer (4 image layers) → Terraform (VM provisioning) → Ansible (config/deploy)
- Variables centralized in `ansible/group_vars/all.yml`, rendered to HCL via `scripts/render-vars.py`

### Initial Observations
- 4 Packer templates (`ubuntu-seed`, `ubuntu-base`, `ubuntu-docker`, `dsv-app`) share ~80% identical variable declarations and source config
- `ssh_config.j2` template is duplicated identically in `roles/deploy/templates/` and `roles/dsv-app/templates/`
- "Wait for cloud-init + dpkg lock" shell block is duplicated in `docker` and `dsv-app` roles
- GitHub deploy key installation (copy + ssh_config) is duplicated in `deploy` and `dsv-app` roles

### Review (3 parallel agents: reuse, quality, efficiency)

**Findings actioned:**

1. `all.yml:49` — `app_dir` hardcoded `adm-ubuntu` instead of `{{ service_account }}`
   - Fixed: now uses `"/home/{{ service_account }}/app/DineSafeViz"`
2. `all.yml:51` — `app_branch` pointed to feature branch `feat/iac-v0.3.0-deploy`
   - Fixed: now `main`
3. `env.j2:20-21` — legacy section hardcoded `DB_HOST=dsv-db` and `DB_PORT=5432`
   - Fixed: now uses `{{ app_analytics_db_host }}` and `{{ app_analytics_db_port }}`
4. `base/tasks/main.yml:36-42` — cloud-init wait lacked dpkg lock check (docker/dsv-app had it)
   - Fixed: upgraded to enhanced version with `fuser /var/lib/dpkg/lock-frontend` polling
5. `cleanup/tasks/main.yml:28-30` — `apt: autoclean` only removes outdated packages
   - Fixed: now `command: apt-get clean` for full cache wipe (proper for template sealing)

**Findings accepted as-is (not worth fixing):**

- Packer variable declarations duplicated across templates — structural HCL limitation
- `ssh_config.j2` duplicated in deploy/ and dsv-app/ — 8 lines, different pipeline stages
- Deploy key tasks duplicated in deploy and dsv-app roles — intentional (bake vs deploy-time)
- Legacy env section in env.j2 — still needed, main branch's docker-compose uses `GF_ADMIN_*` vars
