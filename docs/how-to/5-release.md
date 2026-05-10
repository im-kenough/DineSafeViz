# Release process

This document covers how to version, tag, and publish releases of DineSafeViz.

## How the release pipeline works

The pipeline has two phases:

1. **Draft phase** — every push to `main` triggers the `release-drafter.yml`
   workflow. It creates or updates a draft GitHub Release, grouped by PR label,
   using the template in `.github/release-drafter.yml`. The suggested version
   is resolved automatically from your PR labels (see
   [Versioning](#versioning)).

2. **Publish phase** — pushing a tag matching `v*` triggers the `release.yml`
   workflow, which publishes the matching draft release.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). Release
drafter infers the next version from the highest-priority label on merged PRs
since the last tag:

| Label | Bump |
|---|---|
| `major`, `breaking` | Major (`x.0.0`) |
| `feature`, `enhancement` | Minor (`0.x.0`) |
| `bug`, `fix`, `infosec` | Patch (`0.0.x`) |

If the inferred version is wrong (e.g. you want `v0.2.0` but the draft says
`v0.1.1`), edit the draft release on GitHub before pushing the tag — see step
3 below.

## PR labels

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

## Cutting a release

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
   - The suggested tag (top of the page) matches the version you intend to
     publish. If not, edit the tag field directly on the draft page.

4. **Create an annotated tag.** Use the same version shown on the draft:

   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   ```

5. **Push the tag.**

   ```bash
   git push origin v0.2.0
   ```

6. **Verify the release.** The `release.yml` workflow will publish the draft.
   Confirm the release appears on the
   [Releases page](https://github.com/im-kenough/DineSafeViz/releases) with
   the correct notes.
