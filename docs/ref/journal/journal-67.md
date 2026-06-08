# Journal 67 — Vault-driven proxmox_node variable

## 2026-05-18 — Troubleshoot `no such cluster node 'pve'`

**Problem:** `make bake-base` fails with `500 no such cluster node 'pve'`.
The user's Proxmox node is `yyz-hyp01`, but `proxmox_node` defaults to
`"pve"` everywhere and isn't rendered from vault.

**Root cause:** `render-pkrvars.py` only maps token credentials from the
vault. `proxmox_node` falls through to the HCL default of `"pve"`.

**Fix plan:**
1. Add `vault_proxmox_node` mapping to both render scripts (pkrvars, tfvars)
2. Update `group_vars/all.yml` to reference `{{ vault_proxmox_node }}`
3. Remove stale `default = "pve"` from all 3 Packer HCL files and TF variables
4. Update `.example` files
5. User adds `vault_proxmox_node: "yyz-hyp01"` to vault manually

### Edits

- `infra/scripts/render-pkrvars.py` — added `vault_proxmox_node` to
  `VAULT_TO_PACKER` dict
- `infra/scripts/render-tfvars.py` — added `vault_proxmox_node` to
  `VAULT_TO_TF` dict
- `infra/ansible/group_vars/all.yml` — changed hardcoded `"pve"` to
  `"{{ vault_proxmox_node }}"`
- `infra/packer/ubuntu-base.pkr.hcl` — removed `default = "pve"` from
  `proxmox_node` variable
- `infra/packer/ubuntu-docker.pkr.hcl` — same
- `infra/packer/dsv-app.pkr.hcl` — same
- `infra/terraform/variables.tf` — removed `default = "pve"` from
  `proxmox_node` variable
- `infra/packer/variables.pkrvars.hcl.example` — updated to show
  `"yyz-hyp01"` placeholder
- `infra/terraform/terraform.tfvars.example` — same
