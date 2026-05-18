# Journal 71

## 2026-05-18 — Simplify review of IAC code

### 2026-05-18 14:00
- **Action**: Running `/simplify` review on `feat/iac-v0.3.0-optimize` branch
- **Scope**: 82 files changed vs main; focusing on `infra/` directory (Packer, Terraform, Ansible, Makefile, scripts)
- **Approach**: Launch 3 parallel review agents (reuse, quality, efficiency), then fix findings

### 2026-05-18 14:05 — Review findings aggregated

**Fixed:**

1. **Consolidated `render-pkrvars.py` + `render-tfvars.py` → `render-vars.py`**
   - Both scripts were structurally identical, differing only in the vault-key-to-HCL-key mapping dict
   - New script takes `packer` or `terraform` as positional arg to select mapping
   - Deleted old scripts via `git rm`

2. **Makefile bake macro + single-decrypt `bake-all`**
   - Extracted `define bake` macro parameterized by template filename
   - Individual `bake-*` targets now one-liners: `$(call bake,ubuntu-base.pkr.hcl)`
   - `bake-all` rewritten as explicit recipe that decrypts vault once (was 3 prompts)
   - Updated all `render-tfvars.py` → `render-vars.py terraform` references

3. **Deploy role: 3 tasks → 1**
   - Removed stat check + 2 conditional git tasks (clone vs pull)
   - Single `git` module task handles both cases natively (`update: true` + `accept_hostkey: true`)

4. **Destroy role: 2 conditional compose tasks → 1**
   - Inline Jinja conditional for `-v` flag: `{{ '' if keep_data else ' -v' }}`
   - Kept stat pre-check (avoids ugly error output on missing compose file)

5. **Docker role: removed redundant prereq install**
   - `ca-certificates` and `curl` already installed by base role (Layer 1)
   - Docker role still has its own `update_cache: true` after adding Docker apt repo

**Skipped (not worth fixing / false positives):**

- **Base role apt list cleanup (2 tasks)**: Agent suggested merging, but `file: state=directory` doesn't delete existing files. Original remove+recreate is clearer.
- **Packer plugin blocks duplicated across 3 templates**: HCL constraint — Packer doesn't support shared plugin blocks across templates.
- **Packer variable declarations duplicated**: Same HCL constraint. Documented as intentional.
- **Hardcoded values in Packer templates vs group_vars**: Valid concern but architectural — would require extending render-pkrvars to emit non-secret config values. Out of scope for simplify pass.
- **Terraform defaults duplicated vs group_vars**: Same — render-tfvars only emits secrets. Extending it is a design decision, not a simplification.
- **Section-header comments in Ansible**: Style preference. Task `name:` fields are self-documenting, but headers aid navigation in 200+ line files.
- **Docker smoke test runs every bake**: Acceptable for template validation. Adds minimal time vs the full Packer build.
