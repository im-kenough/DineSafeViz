# Release process

This document covers how to version, tag, and publish releases of DineSafeViz.

## 1. How the release pipeline works

The pipeline has two phases:

1. **Draft phase** — every push to `main` triggers the `release-drafter.yml`
   workflow. It creates or updates a draft GitHub Release, grouped by PR label,
   using the template in `.github/release-drafter.yml`. The suggested version
   is resolved automatically from your PR labels (see
   [2. Versioning](#2-versioning)).

2. **Publish phase** — pushing a tag matching `v*` triggers the `release.yml`
   workflow, which finds the draft release whose tag matches and publishes it.

### 1.1 Release Drafter components

- `.github/workflows/release-drafter.yml`
  - **Triggers:** push to `main`, pull request opened/reopened/synchronized.
  - **What it does:** Runs the [release-drafter/release-drafter](https://github.com/release-drafter/release-drafter) action. On each trigger it rebuilds a single draft release containing categorized notes for all PRs merged since the last published tag. The draft's version, title, body, and tag are all regenerated from the template on every run.

- `.github/release-drafter.yml`
  - **Not a workflow** — this is the configuration file consumed by the `release-drafter` action.

- `.github/workflows/release.yml`
  - **Triggers:** push of a tag matching `v*`.
  - **What it does:** Queries the GitHub API for a draft release whose `tag_name` matches the pushed tag. If found, it PATCHes the release to `draft: false` (publishing it). If no matching draft exists, the workflow fails with an error.

## 2. Versioning

This project follows [Semantic Versioning](https://semver.org/). Release
drafter infers the next version from the highest-priority label on merged PRs
since the last tag:

| Label | Bump |
|---|---|
| `major`, `breaking` | Major (`x.0.0`) |
| `feature`, `enhancement` | Minor (`0.x.0`) |
| `bug`, `fix`, `infosec` | Patch (`0.0.x`) |

The resolver picks the **highest priority bump present**, not cumulative bumps.
Five `feature` PRs still result in a single minor bump.

If the inferred version is wrong (e.g. you want `v0.2.0` but the draft says
`v0.1.1`), override it on the draft before pushing the tag — see
[3.2 Overriding the version](#32-overriding-the-version).

### 2.1 PR labels

Apply exactly one type label to every PR before merging. Release drafter uses
these to categorize entries in the release notes.

| Label | Category in release notes |
|---|---|
| `infosec` | Security |
| `feature`, `enhancement` | Features |
| `ui` | UI |
| `bug`, `fix` | Bug Fixes |
| `infra`, `iac`, `ops`, `dr`, `db` | Infrastructure |
| `ci-cd`, `github_actions` | CI/CD |
| `build`, `dependencies`, `python`, `docker` | Build & Dependencies |
| `documentation` | Documentation |
| `refactor`, `chore` | Maintenance |

Dependabot PRs are labeled automatically via `.github/dependabot.yml`.

<!-- prettier-ignore -->
> [!NOTE]
> A PR with no matching label still appears in the release notes, but it
> lands in an uncategorized section. Always apply a label before merging.

## 3. Release instructions

### 3.1 Cutting a release

1. **Confirm `main` is ready.** Verify all intended PRs are merged and CI
   passes.

2. **Check the current version.**

   ```bash
   git tag --sort=-version:refname | head -5
   ```

3. **Review the draft release.** Open the
   [Releases page](https://github.com/im-kenough/DineSafeViz/releases) and
   open the draft. Verify:
   - The release notes look correct.
   - The **Tag** field (top of the page) matches the version you intend to
     publish. If not, edit it to match (e.g., `v0.3.0`). The publish workflow
     matches on this tag name — if it doesn't match your git tag exactly, the
     workflow will fail.

4. **Create an annotated tag.** Use the same version shown on the draft:

   ```bash
   git tag -a v0.3.0 -m "Release v0.3.0"
   ```

5. **Push the tag.**

   ```bash
   git push origin v0.3.0
   ```

6. **Verify the release.** The `release.yml` workflow will publish the draft.
   Confirm the release appears on the
   [Releases page](https://github.com/im-kenough/DineSafeViz/releases) with
   the correct notes.

### 3.2 Overriding the version

Release Drafter resolves the version from PR labels. If your release includes
only dependency bumps or bug fixes but you want a minor (or major) version
bump, override it manually:

1. Open the draft release on the
   [Releases page](https://github.com/im-kenough/DineSafeViz/releases).
2. Click the **Tag** dropdown at the top of the draft edit page.
3. Clear the existing tag (e.g. `v0.1.1`) and type the desired tag
   (e.g. `v0.2.0`). Select **Create new tag on publish** if prompted.
4. Update the **Release title** to match (e.g. `v0.2.0`).
5. In the release body, find the "Full Changelog" link at the bottom and
   update the tag in the URL to match:
   ```
   .../compare/v0.1.0...v0.2.0
   ```
6. Click **Save draft** (do not click Publish — the workflow handles that).

The git tag you push in the next step must match this tag name exactly.

> [!CAUTION]
> Release Drafter overwrites the draft (including the tag field) on the next
> push to `main`. Only override the version when you are ready to immediately
> tag and publish.

## 4. Notes

### 4.1 How the draft accumulates changes

Release Drafter maintains a **single draft release** at a time. Each push to
`main` triggers a full rebuild — it re-queries all PRs merged since the last
published tag, re-categorizes them, and regenerates the body from scratch. The
draft grows as more PRs merge; it is not appending incrementally.

### 4.2 Release Drafter vs GitHub's native release notes

GitHub has a built-in "Generate release notes" button / `--generate-notes` CLI
flag. This produces a flat PR list with no categorization. Release Drafter is a
separate system that uses `.github/release-drafter.yml` to produce categorized,
templated notes. The two are independent — our pipeline uses Release Drafter.

### 4.3 Why `release.yml` uses the GitHub API instead of `softprops/action-gh-release`

`softprops/action-gh-release` creates a **new** release on tag push. It does
not find or publish an existing draft. This caused duplicate releases (one
empty published release from `softprops`, plus the draft still sitting
unpublished). The current `release.yml` uses `gh api` to find the draft by tag
name and PATCH it to `draft: false`, preserving the Release Drafter notes.

### 4.4 Release Drafter cannot target historical commits

Release Drafter always operates against the current tip of `main`. It cannot
generate formatted notes for a past commit. For retroactive releases, use
`gh release create` with `--generate-notes` (GitHub's native format) or write
the body manually.