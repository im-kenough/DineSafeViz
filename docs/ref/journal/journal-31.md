# Journal 31

## 2026-05-07 — Update release-drafter.yml with Security category and full label coverage

### Context
User requested adding a Security category for the `infosec` label, and a review of all GitHub labels to ensure relevant ones are mapped in the release-drafter template.

### Labels audit
Ran `gh label list` to retrieve all 25 GitHub labels. Cross-referenced against existing release-drafter categories.

**Previously unmapped labels:**
- `infosec` — IT security, IAM, secrets management → new 🔒 Security category
- `ui` — UI changes → new 🎨 UI category
- `infra`, `iac`, `ops`, `dr`, `db` — infrastructure/ops concerns → new 🏗️ Infrastructure category
- `refactor`, `chore` — internal maintenance → new 🔧 Maintenance category
- `github_actions` — GH Actions updates → added to existing ⚙️ CI/CD
- `python`, `docker` — language/runtime bumps → added to existing 🔨 Build & Dependencies

**Not mapped (no release note value):**
- `duplicate`, `invalid`, `wontfix`, `question`, `help wanted`, `good first issue` — triage/meta labels, not release-relevant

### Files edited
- `.github/release-drafter.yml` — added 4 new categories, extended 2 existing, added `infosec` to patch version resolver
