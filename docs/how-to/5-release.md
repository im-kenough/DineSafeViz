# Release process

This document covers how to version, tag, and publish releases of DineSafeViz.

## How the release pipeline works

Releases are fully automated once you push a version tag. The pipeline has
two parts:

1. **Tag push** — pushing a tag matching `v*` to `main` triggers the
   `release.yml` workflow.
2. **Release creation** — the workflow calls `softprops/action-gh-release`,
   which creates a published GitHub Release and auto-generates release notes
   using GitHub's built-in generator (`generate_release_notes: true`).

GitHub's built-in generator groups PRs into categories based on labels. The
categories are configured in `.github/release.yml` (see
[Configuring release notes categories](#configuring-release-notes-categories)
below). The file `.github/release-drafter.yml` is **not currently wired to
any workflow** and has no effect on releases.

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **Major** (`x.0.0`) — breaking changes.
- **Minor** (`0.x.0`) — new features, backward compatible.
- **Patch** (`0.0.x`) — bug fixes, backward compatible.

## PR labels

GitHub's release notes generator uses PR labels to group entries under the
correct heading. Apply exactly one type label to every PR you open:

| Label | Category in release notes |
|---|---|
| `enhancement` | Features |
| `bug` | Bug fixes |
| `ci-cd` | CI/CD |
| `build` | Build & dependencies |
| `documentation` | Documentation |

Dependabot PRs are labeled automatically via `.github/dependabot.yml`.

<!-- prettier-ignore -->
> [!NOTE]
> A PR with no matching label still appears in the release notes, but it
> lands in an uncategorized section. Always apply a label before merging.

## Cutting a release

Follow these steps to publish a new release.

1. **Confirm `main` is ready.** Verify all intended PRs are merged and CI
   passes.

2. **Check the current version.**

   ```bash
   git tag --sort=-version:refname | head -5
   ```

3. **Create an annotated tag.** Replace `v0.2.0` with the next version:

   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   ```

4. **Push the tag.**

   ```bash
   git push origin v0.2.0
   ```

5. **Verify the release.** Open the
   [Releases page](https://github.com/im-kenough/DineSafeViz/releases) and
   confirm the new release was created with the correct notes.

## Configuring release notes categories

GitHub's built-in generator reads `.github/release.yml` for category
definitions. This file does **not** exist yet — without it, GitHub lists all
PRs in a single uncategorized block.

To enable grouping, create `.github/release.yml` with the following content:

```yaml
changelog:
  categories:
    - title: "🚀 Features"
      labels:
        - enhancement
        - feature
    - title: "🐛 Bug Fixes"
      labels:
        - bug
        - fix
    - title: "⚙️ CI/CD"
      labels:
        - ci-cd
    - title: "🔨 Build & Dependencies"
      labels:
        - build
        - dependencies
    - title: "📚 Documentation"
      labels:
        - documentation
    - title: "🔖 Other"
      labels:
        - "*"
```

<!-- prettier-ignore -->
> [!IMPORTANT]
> `.github/release.yml` (GitHub native) and `.github/release-drafter.yml`
> (release-drafter action) are separate tools with different config formats.
> The current workflow uses GitHub native generation. The
> `release-drafter.yml` file is inert until a workflow that invokes the
> `release-drafter/release-drafter` action is added.
