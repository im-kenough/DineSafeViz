# Journal 52

## 2026-05-10 — Tasks 6, 7, 8: Packer Templates (Layers 1, 2, 3)

### Goal
Create 4 files:
- `infra/packer/ubuntu-base.pkr.hcl` (Layer 1, VM 9000→9100)
- `infra/packer/ubuntu-docker.pkr.hcl` (Layer 2, VM 9100→9101)
- `infra/packer/dsv-app.pkr.hcl` (Layer 3, VM 9101→9102)
- `infra/packer/variables.pkrvars.hcl.example`

Make 3 separate commits, one per task.

### Context
Golden image pipeline: seed cloud image (9000) → ubuntu-base (9100) → ubuntu-docker (9101) → dsv-app (9102).
Each template uses proxmox-clone builder + Ansible provisioner pointing to the corresponding playbook.
dsv-app adds `ansible_vault_password_file` variable and conditional `extra_arguments` for vault decryption.

### 2026-05-10 — Confirmed infra/packer directory exists (empty)

### 2026-05-10 — Created ubuntu-base.pkr.hcl
`infra/packer/ubuntu-base.pkr.hcl` written exactly as specified.
Committed: `feat(infra): add Packer template for ubuntu-base (Layer 1)` → ed5b710

### 2026-05-10 — Created ubuntu-docker.pkr.hcl
`infra/packer/ubuntu-docker.pkr.hcl` written exactly as specified.
Committed: `feat(infra): add Packer template for ubuntu-docker (Layer 2)` → c3a632d

### 2026-05-10 — Created dsv-app.pkr.hcl and variables.pkrvars.hcl.example
`infra/packer/dsv-app.pkr.hcl` written exactly as specified.
`infra/packer/variables.pkrvars.hcl.example` written exactly as specified.
Committed: `feat(infra): add Packer template for dsv-app (Layer 3) and vars example` → 775798b
