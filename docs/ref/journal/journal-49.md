# Journal 49

## 2026-05-10 — Task 3: Ansible Base Role (Layer 1 — OS Hardening)

### Goal
Create 5 files for the Ansible `base` role and its Packer playbook:
- `infra/ansible/roles/base/templates/sshd_config.j2`
- `infra/ansible/roles/base/files/jail.local`
- `infra/ansible/roles/base/handlers/main.yml`
- `infra/ansible/roles/base/tasks/main.yml`
- `infra/ansible/playbooks/packer-base.yml`

### Context
Task 3 of 19. Tasks 1–2 created the directory structure and Ansible config/group_vars.
This role is Layer 1 of a 3-layer golden image pipeline (base → docker → app).
It runs during Packer builds via packer-base.yml.

### 2026-05-10 — Checked existing structure
Command: `ls infra/ansible/roles/base/`
Result: `files  handlers  tasks  templates` — directories already exist from Task 1.

Playbooks directory was empty (no files yet).

### 2026-05-10 — Created all 5 files
Files created exactly as specified:
- `templates/sshd_config.j2`: Hardened SSH config template (key-only, no root login)
- `files/jail.local`: fail2ban SSH jail config
- `handlers/main.yml`: Restart handlers for sshd and fail2ban
- `tasks/main.yml`: Full OS hardening tasks (service account, apt, SSH, UFW, fail2ban, unattended-upgrades, timezone/NTP/DNS, cleanup)
- `playbooks/packer-base.yml`: Packer playbook that applies the base role

### 2026-05-10 — Committed
Committed with: `feat(infra): add Ansible base role — OS hardening, SSH, UFW, fail2ban`
