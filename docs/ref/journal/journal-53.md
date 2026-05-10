# Journal 53

## 2026-05-10 — Tasks 9, 10: Ansible Deploy Role/Playbook and Destroy Role/Playbook

### Goal
Create 5 files:
- `infra/ansible/roles/deploy/templates/env.j2`
- `infra/ansible/roles/deploy/tasks/main.yml`
- `infra/ansible/playbooks/deploy-dsv.yml`
- `infra/ansible/roles/destroy/tasks/main.yml`
- `infra/ansible/playbooks/destroy-dsv.yml`

Make 2 separate commits, one per task.

### Context
- `app_dir` = /home/adm-ubuntu/app/DineSafeViz
- `app_repo` = git@github.com:im-kenough/DineSafeViz.git
- `app_branch` = main
- `vm_ip` = 10.0.20.80
- `service_account` = adm-ubuntu
- Vault vars: vault_db_name, vault_db_user, vault_db_password, vault_analytics_admin_user, vault_analytics_admin_password

### 2026-05-10 — Confirmed role directories exist (empty tasks/templates subdirs)

### 2026-05-10 — Created deploy role files
- `infra/ansible/roles/deploy/templates/env.j2` — Jinja2 template for .env file from vault secrets
- `infra/ansible/roles/deploy/tasks/main.yml` — wait_for_connection, clone/pull repo, template .env, docker compose up, health check
- `infra/ansible/playbooks/deploy-dsv.yml` — playbook targeting dsv hosts, loads vault secrets, applies deploy role

### 2026-05-10 — Committed Task 9
