# Journal 45 — Fix release workflow

## 2026-05-10 — Diagnosing release pipeline conflict

**Problem**: User's release process creates duplicate releases. Root cause identified in the interaction between `release-drafter.yml` and `release.yml` workflows.

### Analysis

The user has two workflows:
1. `release-drafter.yml` — runs on push to `main`, creates/updates a draft release with auto-resolved version (e.g., `v0.1.1`)
2. `release.yml` — runs on tag push `v*`, uses `softprops/action-gh-release@v3` which creates a **new** empty release

The conflict:
- Release Drafter creates draft with tag `v0.1.1` (based on PR labels — only patch-level labels present)
- User edits draft to `v0.2.0` and saves
- User pushes `v0.2.0` tag
- `softprops/action-gh-release` doesn't find the draft (it was originally created under `v0.1.1`) and creates a **second**, empty `v0.2.0` release

### Root causes
1. `softprops/action-gh-release` creates new releases rather than publishing existing drafts
2. The version resolver infers `v0.1.1` because merged PRs lack `feature`/`enhancement` labels (they're `build`/`dependencies`)
3. Even after editing the draft tag in the UI, the `softprops` action doesn't match against existing drafts reliably

### Fix applied
- Replaced `softprops/action-gh-release` in `release.yml` with `gh api` calls that find the draft by tag name and PATCH it to `draft=false`
- Updated `docs/how-to/5-release.md` to emphasize that the draft's Tag field must exactly match the git tag being pushed
- The version-resolver issue (v0.1.1 vs v0.2.0) is a labeling problem: PRs need `feature`/`enhancement` labels for a minor bump
