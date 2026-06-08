# Journal 48

## 2026-05-10 — Task 2: Ansible Configuration, Inventory, and Group Variables

### Goal
Create three Ansible configuration files under `infra/ansible/`:
- `ansible.cfg`
- `inventory/hosts.yml`
- `group_vars/all.yml`

### Context
Task 2 of 19 in the DineSafeViz IaC plan. Task 1 already created the directory structure. These files provide the base Ansible configuration that all subsequent roles and playbooks depend on.

### 2026-05-10 — Checked existing structure
Command: `ls /home/sam/SCM/github/DineSafeViz/infra/ansible/`
Result: `group_vars  inventory  playbooks  roles  vault` — directories exist, ready to populate.

### 2026-05-10 — Created ansible.cfg
File: `infra/ansible/ansible.cfg`
Sets inventory path, remote user, SSH key, disables host key checking and retry files. Configures sudo privilege escalation.

### 2026-05-10 — Created inventory/hosts.yml
File: `infra/ansible/inventory/hosts.yml`
Defines single host `yyz-app-dsv01` at `10.0.20.80` under group `dsv`.

### 2026-05-10 — Created group_vars/all.yml
File: `infra/ansible/group_vars/all.yml`
Centralized non-secret config for Proxmox, network, template IDs, VM spec, service account, application, and Docker settings.

### 2026-05-10 — Committed
Committed all three files with message: `feat(infra): add Ansible config, inventory, and centralized variables`
