# Journal 78 - IaC Code Reuse Audit

## 2026-05-19 -- IaC code reuse review

Read every file under `infra/` to verify six suspected code reuse / duplication issues.

### Files read
- `infra/packer/ubuntu-base.pkr.hcl`
- `infra/packer/ubuntu-docker.pkr.hcl`
- `infra/packer/dsv-app.pkr.hcl`
- `infra/packer/ubuntu-seed.pkr.hcl`
- `infra/packer/variables.pkrvars.hcl.example`
- `infra/Makefile`
- `infra/ansible/inventory/hosts.yml`
- `infra/ansible/group_vars/all.yml`
- `infra/ansible/roles/docker/tasks/main.yml`
- `infra/ansible/roles/dsv-app/tasks/main.yml`
- `infra/ansible/roles/deploy/templates/env.j2`
- `infra/ansible/vault/example-secrets.yml`
- `infra/scripts/render-vars.py`
- `infra/ansible/roles/base/tasks/main.yml`
- `infra/ansible/roles/deploy/tasks/main.yml`
- `infra/ansible/roles/cleanup/tasks/main.yml`
- `infra/terraform/variables.tf`
- `infra/terraform/main.tf`

### Findings

All six items confirmed. Full details provided in conversation response.
