# Journal 1

## 2026-08-11

### 2026-08-11 — Session start: rewrite all active docs/ files with write-better-docs

Task: apply the `write-better-docs` skill (Diátaxis + Google style + ASD-STE100) to
all active documentation under `docs/`.

Scoping decisions (confirmed with user via AskUserQuestion):

- Scope: **active docs only**. Exclude both `old-ignore/` directories and empty stubs
  (`docs/ref/infra/infra.md`, `docs/ref/arch/overview-iac.md`, `docs/ref/arch/arch-env.md`).
- Delivery: **edit in place, batch by batch**, pausing after each batch for review.

Survey result: 57 `.md` files total, ~7,118 lines. After excluding old-ignore and stubs,
roughly 30 active files remain.

Flagged duplication: `docs/how-to/1-install/1-workstation.md` (77 lines) vs
`1-workstation-v0.4.0.md` (219 lines) — one likely supersedes the other.

Planned batches:

1. `docs/how-to/` top-level guides (2-piv, 3-redeploy-guide, 4-admin-guide, 5-release, 6-rotate-secrets)
2. `docs/how-to/1-install/` (README + numbered install steps)
3. `docs/ref/arch/` core architecture docs
4. `docs/ref/arch/design-planning/` (v0.4.0 planning docs)
5. `docs/ref/` miscellaneous reference docs

Read all skill reference files first: diataxis-1-summary, diataxis-3-how-to,
diataxis-4-reference, diataxis-5-explaination, google-doc-style-guide, word-list (partial,
grep for specifics), asd-ste100.

### 2026-08-11 — Batch 1 complete: docs/how-to top-level guides

Rewrote 5 how-to guides. Preserved all commands, container names, env vars, ports, and URLs
verbatim. Changes:

- `2-piv.md`: retitled "Post implementation verification" → "Verify a deployment". Fixed
  heading levels (h3 → h2, no skipped levels). Removed the word "healthy" (Google word list).
  Stated expected result before each command.
- `3-redeploy-guide.md`: restructured "Case 1/2/3" into task-oriented sections with
  conditional imperatives ("To do x, run y"). Kept the three `make` commands identical.
- `4-admin-guide.md`: separated the login how-to from the Docker command cheat sheet
  (Diátaxis how-to vs reference), kept in one file. Consolidated duplicate rebuild command
  blocks that appeared twice at the end (redundant noise). Turned the inline "wipes volume"
  code comment into a "Reset a partial database load" section. NOTE: login uses port 3000,
  which differs from 2-piv's port 5000 — left as-is (real difference, not touched).
- `5-release.md`: surgical edits only (file was already well-written). Fixed `e.g.` →
  `for example`, future tense → present ("will publish" → "publishes", "will fail" →
  "fails"), removed a semicolon, "dropdown" → "menu".
- `6-rotate-secrets.md`: removed "we'll"/"you'll", "Github" → "GitHub", "unchecked" →
  "Clear ... " (checkbox), imperative numbered steps. FIXED filename inconsistency: prose said
  `secrets.yaml` but every command uses `secrets.yml` — aligned prose to `.yml` (commands
  confirm the real filename). Flag to user for confirmation.

Paused for user review before Batch 2.

### 2026-08-11 — Batch 2 complete: docs/how-to/1-install guides

Key finding: `1-workstation.md` (Proxmox) and `1-workstation-v0.4.0.md` (Azure AKS) are NOT
duplicates — they target different architectures. User confirmed via AskUserQuestion: rewrite
prose of the v0.4.0 file but keep its trailing `# Old` scratch section as-is.

Rewrote 8 files. Preserved all commands and inline code comments verbatim. Notable changes:

- Fixed 3 broken cross-links (correctness):
  - `README.md`: links pointed to `docs/how-to/install/…` (wrong dir, wrong base) → fixed to
    bare sibling links (`1-workstation.md`, etc.).
  - `5-create-vm-image.md`: linked to `deploy-guide-iac.md` (now in old-ignore) → `6-deploy.md`.
  - `6-deploy.md`: prereq linked to `docs/how-to/install/README.md` → `README.md`.
- Standardized `IAC` → `IaC` (defined "infrastructure as code (IaC)" on first use).
- `2-setup-proxmox.md`: fixed typo "paker" → "Packer". Made the terraform "save token"
  sentence consistent with the packer one.
- `1-workstation-v0.4.0.md`: fixed broken heading hierarchy (had ####, then jumped to ## for
  "Install helmfile binary" and "Verify the installation"). Normalized to h2 parent + h3 per
  tool. Kept the Helm concept explanation but tightened it into a bulleted glossary. Kept the
  `# Old` section byte-for-byte per user decision.
- `6-deploy.md`: removed empty `## Appendix` heading (Google: no empty headings). Grouped the
  operations under "## Other operations" (h3 children) and kept Troubleshooting as its own h2.
  Sentence-cased all headings, present tense, `repo` → `repository`.

Paused for user review before Batch 3.

### 2026-08-11 — Batch 3 complete: docs/ref/arch core docs

User amended scope: exclude `docs/ref/arch/design-planning/` entirely (dropped former Batch 4).
Excluded empty stubs (`arch-env.md`, `overview-iac.md`) and `old-ignore/`.

Batch 3 split into two groups:

FINISHED docs (already high quality — surgical edits only, per "don't fix what isn't broken"):
- `arch-security.md`: "Design Principles" → sentence case, `IAC` → `IaC` (tables), "blast radius"
  → "affected area" (word list), "a Ubuntu" → "an Ubuntu", fixed broken link
  `docs/how-to/6-rotate-secrets.md` → `../../how-to/6-rotate-secrets.md`.
- `arch-dr.md`: title "Disaster Recovery & Resiliency" → "Disaster recovery and resiliency"
  (ampersand + case), "TO do"/"To do" → "TODO". Kept the placeholder TODOs.
- `arch-app.md`: "dropdown" → "menu" (word list).
- `arch-data.md`: "In the future" → "A planned" (word list). Otherwise untouched.
- `arch-ci-cd.md`, `arch-testing.md`, `arch-checklist.md`: NO edits — already compliant.
- `arch-iac.md`: rewritten. Fixed mid-doc `# Image Pipeline` h1 → h2, typos ("THe", "dvs-app"
  → "dsv-app", "Dinesafeviz"), "a ubuntu"→"an Ubuntu". Fixed 2 broken links (`secrets-mgt.md`,
  `../../ops/index.md` — neither exists) → arch-security.md and 6-deploy.md.

SKELETON docs (placeholders preserved as TODO markers, did NOT fabricate content):
- `README.MD`: fixed typos (Architectual, architectueral, COde, Coordianting, Comming,
  infrastrucutre), Github → GitHub. Built the actual table of contents the doc asked for
  (all target files exist) — ADDED content, flagged to user. Converted self-notes to TODO.
- `arch-monitoring.md`: fixed typos (centeralized, DineSaveViz), sentence-case headings,
  "Alert Manager" → "Alertmanager", empty sections marked TODO.
- `arch-net.md`: DNS section formatted (kept dig output verbatim), "CLoudflare" → "Cloudflare",
  IPAM placeholders kept as TODO (x.x.x.x, diagrams).

FLAGGED factual inconsistencies (did NOT change — need author decision):
1. Grafana version: `arch-data.md` says 11.6, `arch-app.md` pins image `grafana:11.2.0`.
2. Analytics reverse proxy: `arch-app.md` says the Flask proxy was REMOVED and nginx handles
   `/analytics/`; `arch-data.md` still says Flask embeds it via a reverse proxy (stale).
3. Bridge script name: `arch-iac.md` says `render-vars.py`; how-to guides use `render-tfvars.py`.
4. `arch-checklist.md` links to `arch-design-decision.md`, which does not exist (design-planning
   excluded; likely aspirational).

Paused for user review before Batch 5.

### 2026-08-11 — Batch 5 complete: docs/ref miscellaneous docs

Left untouched (already compliant): `azure-component-inventory.md`, `project-management.md`.

- `data.md`: fixed two `# H1`s → single h1 + h2s. Sentence-cased Title Case headings
  ("Data Sources", "Current Data", "Data Dictionary", "Database Schema"). Merged the two
  redundant "Historical Data" / "Historical data (2001-2015)" headings. "csv files" → "CSV
  files". Preserved all tables, sample rows, and enum lists verbatim.
- `troubleshooting.md`: fixed heading hierarchy (h3 topics that were siblings → h2). Rewrote
  the informal duplicate "doesn't load in firefox" scratch note into a clean "Dashboard shell
  loads but shows no data" subsection (distinct ad-blocker cause — kept the information).
  "healthy" → "running", "may" → "might".
- `workflow.md`: fixed broken link `docs/how-to/5-release.md` → `../how-to/5-release.md`.
  Removed empty bullet. Converted raw URL dump into a "References" list with descriptive link
  text. "Antipatterns" → "Practices to avoid" (word list). "gitsubmodules" → "git submodules".
  Kept "Coming soon" WIP markers.
- `known-issues.md`: `IAC` → `IaC`, `e.g.` → `for example`, title sentence case.
- `use-cases.md`: consistent capitalization, sentence-case headings. FIXED copy-paste bug:
  UC-SYS-06 "C2 (staging)" described reverting *production* → corrected to *staging*. "cut-off"
  → "cutover" (the DR term used elsewhere).

All five documentation batches complete. Next: verify docs against current code.

### 2026-08-11 — Verification pass: docs vs current code

Checked doc claims against docker-compose.yml, src/, infra/. Sources of truth:
docker-compose.yml, nginx.conf, init.sql, refresh.py, Dockerfile, requirements-dev.txt,
infra/Makefile, infra/scripts/render-vars.py.

CONFIRMED ACCURATE:
- `arch-app.md`: nginx host :8080, dsv-app :8000 (internal), grafana :3000; Flask proxy removed
  (app.py has no proxy route — grep confirmed); 19-col schema; roles; routes.
- `init.sql`: 19 columns + `dinesafe_app` (SELECT) + `dinesafe_migrator` (ALL) — matches
  data.md unified schema and arch-app/arch-security.
- `refresh.py`: normalize, min_inspection_date, map_row, HISTORICAL/RECENT_COLUMN_MAP,
  INSPECTIONS_COLUMNS, COPY bulk insert — matches arch-data + arch-testing.
- `pytest==9.0.3` (requirements-dev.txt) — matches arch-testing.
- `render-vars.py` exists and Makefile uses it — arch-iac.md CORRECT. (My earlier flag #3
  resolved: the how-to `render-tfvars.py` was the wrong name, not arch-iac.)
- Dockerfile base `python:3.14-slim-bookworm`, nonroot 65532 — matches arch-app.

STALE — FIXED (code authoritative):
- `arch-data.md`: `postgres:17.9` → `17.0` (compose); Grafana `11.6` → `11.2.0` (compose);
  "embedded in Flask app via reverse proxy" → nginx reverse-proxies at :8080; removed
  "Grafana reverse proxy" from app.py file description.
- `2-piv.md`: all `localhost:5000` → `localhost:8080` (nginx entry point; loopback, UFW n/a).
- `troubleshooting.md`: dashboard URLs 5000 → 8080; port-conflict section updated to
  `dsv-nginx` `8080:80` (was `dsv-app` `5000:5000`, which does not exist in compose).
- `arch-testing.md`: removed the "Analytics proxy (test_proxy.py)" section — file does not
  exist (proxy removed with the Flask proxy).
- `data.md`: historical data does NOT live at `src/dsv-db/2023-04-11 - Dinesafe Historical
  data/` (dir absent) — refresh.py downloads the ZIP at runtime; reworded.
- `6-deploy.md`: `render-tfvars.py` → `render-vars.py terraform` (matches Makefile line 71).

FLAGGED — NOT auto-fixed (needs author decision; code is self-contradictory):
- PORT 5000 vs 8080 in VM deployment: `infra/ansible/roles/dsv-app/tasks/main.yml` opens UFW
  5000, but compose serves nginx on 8080. So `arch-security.md` firewall table (5000) and
  `6-deploy.md` ("http://10.0.20.80:5000") AGREE with the Ansible code but DISAGREE with
  compose. Left VM-facing docs at 5000 to match the current Ansible role; the real fix is
  likely to update the UFW rule to 8080 and then the docs. Author must reconcile.
- Root `README.md` (repo root, outside docs/ scope) not verified/edited.
- `arch-checklist.md` links to `arch-design-decision.md` (does not exist; design-planning
  excluded from scope).

Verification complete.

### 2026-08-11 — Reconcile port 5000 → 8080 (code + docs) and update root README

User decision: standardize on 8080 (the nginx entry point). Resolved the flagged
5000-vs-8080 drift.

Code:
- `infra/ansible/roles/dsv-app/tasks/main.yml`: UFW rule 5000 → 8080 (the root-cause bug —
  compose serves nginx on 8080 but UFW opened 5000, so external access was broken).

Docs:
- `arch-security.md`: firewall table `5000 | Flask web app` → `8080 | nginx reverse proxy`;
  network isolation "5000 (Flask)" → "8080 (nginx)" + noted dsv-app internal 8000.
- `6-deploy.md`: `http://10.0.20.80:5000` → `:8080`.
- `troubleshooting.md`: Firefox error-message example `localhost:5000` → `8080`.
- Root `README.md`: rewrote to style. Added the missing `dsv-nginx` edge service (entry point
  on 8080). Fixed `IAC` → `IaC`, typos (selfhosted, foot print, visualises, one off, Grafana
  based), subject-verb ("configuration are" → "is"), broken link
  `DineSafeViz/infra/ansible/vault/secrets.yml` → `infra/ansible/vault/secrets.yml`, removed a
  stray bare path line, normalized headings to sentence case, "Coming Soon (™️)" → "coming
  soon".

Verified: no `5000` references remain in code or docs (grep clean, excluding the journal's own
history log and an unrelated `app.py` metrics histogram bucket). Port standardization complete.

### 2026-08-11 — Centralize secrets, service accounts, usernames in arch-security.md

Audited whole repo (docker-compose.yml, init.sql, group_vars/all.yml, example-secrets.yml,
roles/deploy/templates/env.j2, render-vars.py, packer/*.hcl, terraform/variables.tf) to build
the authoritative identity inventory. Rewrote arch-security.md to be the single source with a
1-sentence "what it is used for" per item.

Authoritative facts (from code, not prior docs):
- Vault holds ONLY 6 secrets: vault_proxmox_api_token_secret, vault_packer_api_token_secret,
  vault_db_password, vault_db_app_password (optional), vault_analytics_admin_password,
  vault_github_deploy_keys.
- Token IDs (svc-*@pve!*), DB usernames (dinesafe, dinesafe_app), DB name, and Grafana admin
  username are NON-SECRET config in group_vars/all.yml — not vault keys.
- Service accounts/identities: adm-ubuntu (VM + Packer build), root@pve (manual), iac SSH key,
  svc-terraform@pve, svc-packer@pve, GitHub deploy key.
- PostgreSQL roles (init.sql): dinesafe (superuser), dinesafe_app (SELECT), dinesafe_migrator
  (DDL, unused). Grafana: admin + anonymous Viewer.

arch-security.md changes:
- Replaced the wrong "Vault contents" table (which listed token IDs, db_user, db_name,
  analytics_admin_user as vault keys — they aren't) with a corrected 6-secret table + a new
  "Non-secret identifiers (group_vars)" table.
- Corrected "Application credentials" (was `vault_db_user`/`vault_analytics_admin_user` — not
  keys) and added "PostgreSQL roles" and "Grafana identities" tables.
- Expanded "VM automation" to add root@pve and the iac SSH key.
- Added "Planned identities (v0.4.0 AKS)" summarizing the Azure MIs + KV secret, pointing to
  azure-component-inventory.md as authoritative (avoids duplicating the 40-resource table).

FLAGGED (real inconsistencies found, NOT auto-fixed — need author decision):
1. `infra/ansible/vault/example-secrets.yml` defines `vault_app_analytics_db_password`, but
   `env.j2` consumes `vault_db_password` and `vault_db_app_password`. Following the example
   vault yields an EMPTY superuser password → broken deploy. The example is out of sync with
   the deploy template.
2. `docs/how-to/1-install/4-setup-app.md`'s vault YAML lists keys the code never reads
   (`vault_proxmox_node`, `vault_*_api_token_id`, `vault_db_user`, `vault_db_name`,
   `vault_analytics_admin_user`) and omits `vault_db_app_password`. Harmless-but-misleading.
Both should be reconciled to the 6-key list now in arch-security.md.
