# Journal 76 — Simplify IAC Code

## 2026-05-19 — Session Start

### Goal
Review and simplify all IaC code in `infra/`, centralizing variables and improving efficiency.

### Files Read
- `infra/Makefile` — orchestration of bake/provision/deploy
- `infra/scripts/render-vars.py` — merges all.yml + vault → HCL output
- `infra/ansible/group_vars/all.yml` — centralized non-secret vars
- `infra/ansible/vault/example-secrets.yml` — vault structure
- `infra/ansible/inventory/hosts.yml` — single target host
- `infra/ansible/playbooks/*.yml` — all 5 playbooks
- `infra/ansible/roles/*/tasks/main.yml` — all 6 roles
- `infra/ansible/roles/*/templates/*.j2` — all templates
- `infra/ansible/roles/base/files/jail.local` — fail2ban config
- `infra/packer/*.pkr.hcl` — all 4 packer templates
- `infra/packer/http/user-data.pkrtpl.hcl` — cloud-init template
- `infra/terraform/*.tf` — main, variables, outputs

### Three parallel review agents dispatched
1. Code Reuse — found env.j2 bug, Packer duplication, Makefile dead code, inventory hardcoding
2. Code Quality — found naming inconsistencies, dead ansible_vault_password_file, unnecessary comments
3. Efficiency — found tfvars secret leak on failure, confirmed apt/docker patterns are correct

### Changes Made (8 files, -41 net lines)

1. **Fixed env.j2 bug** — 4 of 7 variable names were wrong:
   - `vault_db_name` → `app_analytics_db_name`
   - `vault_db_user` → `app_analytics_db_user`
   - `vault_db_password` → `vault_app_analytics_db_password`
   - `vault_analytics_admin_user` → `app_analytics_admin_user`
   - Removed redundant Grafana comment block

2. **Fixed tfvars secret leak** — provision-vm and destroy-vm now cleanup terraform.tfvars even on terraform failure (subshell with ret capture)

3. **Aligned variable names** to reduce render-vars.py mapping surface:
   - all.yml: `proxmox_node_name` → `proxmox_node`
   - all.yml: `packer_build_ip` → `build_ip_base`, `packer_docker_build_ip` → `build_ip_docker`, `packer_app_build_ip` → `build_ip_app`
   - Terraform: `network_bridge` → `proxmox_bridge` (matches all.yml name)
   - render-vars.py: 5 mappings now identity, 1 renamed

4. **Cleaned up Makefile** — removed 15-line commented-out bake-all, removed 2 redundant `packer init` calls in bake-all

5. **Simplified render-vars.py** — replaced `find_all_vars()` 3-path search with script-relative path

6. **Removed dead code** — `ansible_vault_password_file` variable + conditional from dsv-app.pkr.hcl (never set by render-vars.py)

7. **Fixed typo** — stray `"` in example-secrets.yml line 7

### Not changed (assessed, acceptable as-is)
- Packer variable declaration duplication across 3 clone templates (11 shared vars × 3 files). Packer HCL doesn't support shared variable files when building individual templates. Would require switching to directory-based builds with `-only` filters — more complexity than it saves for 3 files.
- Ansible inventory hardcoding (hosts.yml duplicates IP/user from all.yml). Ansible doesn't support Jinja2 in inventory files. A dynamic inventory script is possible but adds complexity for a single-host setup.
- cloud-init wait task duplication in docker + dsv-app roles. Extracting to a shared taskfile is possible but only saves 6 lines across 2 files.
