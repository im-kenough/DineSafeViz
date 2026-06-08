# Journal 66 — Update IaC from GitHub App to Deploy Keys

## 2026-05-18 14:30

**Task:** Update docs and infra code to reflect switch from GitHub App to deploy keys for repo cloning.

**Context:** User already changed the vault key name to `vault_github_deploy_keys` (commit abe36c2) and added deploy key setup steps to the install guide (commit c65ec08). Remaining references to "GitHub App" and `vault_github_app_key` need updating in:

- `infra/ansible/roles/dsv-app/tasks/main.yml` — vault var, file dest, comments
- `infra/ansible/roles/dsv-app/templates/ssh_config.j2` — file path, comments
- `infra/packer/dsv-app.pkr.hcl` — comments
- `docs/how-to/install-guide-iac.md` — vault template comment
- `docs/superpowers/specs/2026-05-10-iac-design.md` — multiple GitHub App refs, vault var
- `docs/superpowers/plans/2026-05-10-iac.md` — multiple GitHub App refs, vault var

Also noted: `docs/ref/arch/arch-security.md` has two references to `vault_github_app_key` — will flag to user.

## 2026-05-18 14:35

Editing infra code files (dsv-app role tasks, ssh_config template, packer template).

Changes:
- `vault_github_app_key` → `vault_github_deploy_keys`
- file destination `github-app-key` → `deploy-key`
- all "GitHub App" references → "GitHub deploy key"

## 2026-05-18 14:40

Editing docs: install guide, design spec, implementation plan.
- Updated vault variable references
- Updated all "GitHub App" terminology to "deploy key"
- Updated file paths from `github-app-key` to `deploy-key`

## 2026-05-18 14:50

Editing `docs/ref/arch/arch-security.md`:
- Vault contents table: `vault_github_app_key` → `vault_github_deploy_keys`
- GitHub access section: rewrote for deploy keys — notes read-only scope,
  ed25519 key type, single-repo scope, file path `/home/adm-ubuntu/.ssh/deploy-key`
- Proxmox API section: expanded from a simple token table to include actual
  service account names (`svc-packer@pve`, `svc-terraform@pve`), custom roles,
  permission sets, and blast-radius analysis for compromised tokens

## 2026-05-18 15:00

`make bake-base` failed with `Error: Unset variable "proxmox_api_url"`.

**Root cause:** `render-pkrvars.py` only maps vault secrets (token ID/secret)
to Packer variables. `proxmox_api_url` is a non-secret value with no default
in the HCL — so it was never provided at runtime. Every other non-secret var
(e.g. `proxmox_node`, `clone_vm_id`) already had defaults; this one was missed.

**Fix:** Added `default = "https://10.0.20.21:8006"` to `proxmox_api_url` in
all three Packer templates (ubuntu-base, ubuntu-docker, dsv-app). Value matches
`group_vars/all.yml`.

## 2026-05-18 15:10

`make bake-base` failed again: `Could not retrieve VM: 500 no such file '/cluster/resources'`

**Root cause:** Packer's `proxmox_url` requires the full API path including
`/api2/json`. Every official example uses e.g. `https://pve.example.com:8006/api2/json`.
Our default was `https://10.0.20.21:8006` (missing the API path suffix). The
plugin constructed incorrect API paths, causing a 500 from Proxmox.

Note: Terraform's bpg/proxmox provider uses `endpoint` which handles the API
path internally, so `group_vars/all.yml` stays as-is. This fix is Packer-only.

**Fix:** Updated default to `https://10.0.20.21:8006/api2/json` in all three
Packer templates + `variables.pkrvars.hcl.example`.
