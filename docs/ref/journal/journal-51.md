# Journal 51

## 2026-05-10 — Task 5: Ansible DSV-App Role (Layer 3)

### Goal
Create 3 files for the Ansible `dsv-app` role and its Packer playbook:
- `infra/ansible/roles/dsv-app/templates/ssh_config.j2`
- `infra/ansible/roles/dsv-app/tasks/main.yml`
- `infra/ansible/playbooks/packer-dsv-app.yml`

### Context
Task 5 of 19. dsv-app role is Layer 3 in the golden image pipeline (base → docker → app).
Sets VM identity (hostname, static IP via netplan) and installs the GitHub App private key
for repo cloning. No repo clone or .env here — that's the deploy playbook (Task 9).
Playbook uses `vars_files: ../vault/secrets.yml` because it needs `vault_github_app_key`.

### 2026-05-10 — Checked existing structure
Command: `ls infra/ansible/roles/dsv-app/`
Result: `tasks  templates` — directories already exist, empty.

Playbooks directory already has `packer-base.yml` and `packer-docker.yml`.

### 2026-05-10 — Created all 3 files
Files created exactly as specified:
- `templates/ssh_config.j2`: SSH config template for GitHub App deploy key
- `tasks/main.yml`: VM identity (hostname, /etc/hosts, netplan static IP), GitHub App key install, SSH config deploy, app directory creation
- `playbooks/packer-dsv-app.yml`: Packer playbook that applies the dsv-app role with vault secrets

### 2026-05-10 — Committed
Committed with: `feat(infra): add Ansible dsv-app role — VM identity and GitHub App key`
