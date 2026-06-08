# Journal 55

## 2026-05-10 — Tasks 12 and 13: render-tfvars.py, render-pkrvars.py, and Makefile

### Goal
- Task 12: Create `infra/scripts/render-tfvars.py` — bridges Ansible Vault to Terraform vars
- Task 13: Create `infra/scripts/render-pkrvars.py` and `infra/Makefile` — orchestrate all IaC ops

### 2026-05-10 — Verified preconditions
- Branch: `feat/iac-v0.3.0` ✓
- Previous journal (54): Task 11 completed (Terraform config) ✓
- `infra/scripts/` directory exists and is empty ✓

### 2026-05-10 — Created infra/scripts/render-tfvars.py
- Maps vault_proxmox_api_token_id → proxmox_api_token_id
- Maps vault_proxmox_api_token_secret → proxmox_api_token_secret
- Made executable with chmod +x

### 2026-05-10 — Tested render-tfvars.py
Command:
```
echo 'vault_proxmox_api_token_id: "svc-terraform@pve!terraform"
vault_proxmox_api_token_secret: "test-secret-123"' | python3 infra/scripts/render-tfvars.py
```
Expected:
```
proxmox_api_token_id = "svc-terraform@pve!terraform"
proxmox_api_token_secret = "test-secret-123"
```

### 2026-05-10 — Committed Task 12
Commit: `feat(infra): add render-tfvars.py — bridges Ansible Vault to Terraform vars`

### 2026-05-10 — Created infra/scripts/render-pkrvars.py
- Maps vault_packer_api_token_id → proxmox_api_token_id
- Maps vault_packer_api_token_secret → proxmox_api_token_secret
- Made executable with chmod +x

### 2026-05-10 — Created infra/Makefile
- Targets: bake-base, bake-docker, bake-dsv-app, bake-all
- Targets: provision-vm, destroy-vm
- Targets: deploy-app, destroy-app, destroy-app-keep-data, redeploy-app, redeploy-app-keep-data
- Targets: up, down, help
- Verified tab indentation (critical for make)

### 2026-05-10 — Tested make help
Output should show formatted list of all targets with descriptions.

### 2026-05-10 — Committed Task 13
Commit: `feat(infra): add Makefile and render-pkrvars.py — orchestrate all IaC ops`
