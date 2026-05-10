# Journal 30

## 2026-05-07 — Redo v0.1.0 release notes with proper categorization

### Context

User reported that release-drafter was not categorizing PRs correctly. They manually updated all closed PRs to use conventional commit titles and applied labels. Task: update `.github/release-drafter.yml` and rewrite the v0.1.0 release body.

### Investigation

Examined existing release-drafter.yml — only had two categories (Features, Bug Fixes), using labels `feature`/`enhancement` and `bug`/`fix`. Missing categories for build, documentation, and CI/CD.

Checked closed PR list with labels and merge dates:
- 25 PRs merged before v0.1.0 tag (2026-04-28)
- PRs #16, #27, #59 have no merge date (closed without merging)
- PRs #56, #57, #65 merged after v0.1.0

Original v0.1.0 release was missing early PRs (#7, #8, #17, #18, #19) that were merged before the release drafter was set up.

### v0.1.0 PRs (all merged before tag)
#7, #8, #17, #18, #19, #20, #21, #22, #23, #24, #25, #26, #33, #35, #36, #42, #43, #44, #46, #47, #49, #50, #51, #52, #55

### Changes made

- `.github/release-drafter.yml`: added CI/CD, Build & Dependencies, Documentation categories; reordered so specific types (CI/CD, build, docs) take priority over generic `enhancement` label
- v0.1.0 release body: rewrote with proper grouped headings via `gh release edit`
2026-05-07 12:00 — Updated release.md and identified release-drafter.yml gap
