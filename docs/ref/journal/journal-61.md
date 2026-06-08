# Journal 61

## 2026-05-12 — Document existing CI/CD architecture

### 2026-05-12 16:00
- **Task:** Read the repo and update `docs/ref/arch/arch-ci-cd.md` with
  current CI/CD state.
- **Investigation:** Searched for CI/CD config files across the repo.
- **Findings:**
  - `.github/workflows/release-drafter.yml` — runs on push to `main` and
    PR events; drafts a categorized release using `release-drafter/release-drafter@v7`.
  - `.github/release-drafter.yml` — config for the action; maps PR labels to
    changelog sections and semver bump rules.
  - `.github/workflows/release.yml` — triggers on `v*` tag push; publishes
    the matching draft release via the GitHub API.
  - `.github/dependabot.yml` — weekly version updates for pip, Docker base
    images, and GitHub Actions.
  - `infra/Makefile` — local IaC orchestration (Packer bake, Terraform
    provision, Ansible deploy); not CI/CD automation per se, but part of the
    deployment story.
- **No CI pipelines found:** No build, test, or lint workflows exist. No
  pre-commit hooks. No container image build/push automation.
- **Action:** Wrote `arch-ci-cd.md` documenting the current state, noting
  gaps.
