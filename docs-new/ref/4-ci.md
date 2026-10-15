# Continuous integration

This page gives a high-level view of how DineSafeViz builds, scans, and
publishes its container images, and how it tracks dependencies and releases.

## Overview

The key CI tasks of DineSafeViz are to:
1. Build and scan the owned images on every pull request
2. Publish scanned images to GitHub Container Registry (GHCR) for deploys
3. Rescan published and upstream images for newly disclosed vulnerabilities
4. Keep dependencies current and draft release notes

CI stops at GHCR. It never deploys. `scripts/deploy.sh` pulls a published tag
onto a VM, and an operator runs it.

## Workflows

All automation lives in `.github/`. There are three workflows and one
Dependabot configuration.

| File                                    | Triggers                                | Does                                                  |
| --------------------------------------- | --------------------------------------- | ----------------------------------------------------- |
| `.github/workflows/images.yml`          | PR, push to `main`, `v*` tag, weekly, manual | Builds, scans, and publishes the owned images    |
| `.github/workflows/release-drafter.yml` | PR, push to `main`                      | Rebuilds the draft release notes                      |
| `.github/workflows/release.yml`         | `v*` tag                                | Publishes the draft release that matches the tag     |
| `.github/dependabot.yml`                | Weekly                                  | Opens PRs for outdated dependencies                   |

## Images

`images.yml` builds two images. Upstream images (nginx, Postgres, Grafana, and
cloudflared) are pinned by tag and digest in the Compose files and are never
rebuilt.

| Image                             | Build context      |
| --------------------------------- | ------------------ |
| `ghcr.io/im-kenough/dsv-app`      | `src/dsv-app`      |
| `ghcr.io/im-kenough/dsv-pipeline` | `src/dsv-pipeline` |

`images.yml` has four jobs. Which jobs run depends on the trigger:

| Job           | Runs on                   | Does                                                                 |
| ------------- | ------------------------- | -------------------------------------------------------------------- |
| `scan`        | PR, push                  | Builds each image for `linux/amd64`, scans it with Trivy             |
| `push`        | Push, after `scan` passes | Rebuilds from the `scan` job's layer cache, pushes to GHCR           |
| `list-images` | Weekly, manual            | Lists the deployed owned tags and the pinned upstream images         |
| `rescan`      | Weekly, manual            | Scans each listed image and uploads the results                      |

### Scan: gate every build

The `scan` job builds each image locally and runs Trivy against it before
anything is pushed.

- **Gate:** the job fails on `CRITICAL` vulnerabilities that have a fix.
  `HIGH` and below, and anything without a fix, never fail the build.
- **Report:** on pushes, a second Trivy pass uploads every severity as SARIF
  to **Security > Code scanning**. On PRs, only the gate's table appears, in
  the job log.
- **Cache:** layers go to the GitHub Actions cache, scoped per image. The
  `push` job reuses them, so the image it pushes is the one that was scanned.

### Push: publish deployable tags

The `push` job runs only on pushes, and only after `scan` passes for both
images. Every deployable tag is immutable. There's no `latest`.

| Trigger        | Tags pushed           | Deployed with           |
| -------------- | --------------------- | ----------------------- |
| Pull request   | None                  | Not deployed            |
| Push to `main` | `main`, `sha-<7>`     | `deploy.sh stg main`    |
| Tag `v0.5.0`   | `0.5.0`, `0.5`        | `deploy.sh prod v0.5.0` |

`deploy.sh stg main` resolves `origin/main` to a commit and pulls the matching
`sha-` tag, never the moving `main` tag. Before it changes anything, it
checks that both images exist in GHCR. If `images.yml` hasn't finished, the
deploy stops.

### Rescan: catch new vulnerabilities

New vulnerabilities are published after an image is built. Every Monday at
06:17 UTC, or on demand, `list-images` builds the scan list from:

- The `main` tag of both owned images
- The latest published release tag of both owned images
- Every pinned upstream image in `docker-compose.yml` and
  `docker-compose.vm.yml`

`rescan` scans each one and uploads the results to code scanning. It never
fails the run. Read the findings in **Security > Code scanning**.

## Releases

Release notes build up automatically, and a tag publishes them.

1. On every PR and every push to `main`, `release-drafter.yml` regenerates
   one draft release. PR labels set the section (for example, `fix` goes to
   **Bug Fixes**) and the next version (`breaking` is major, `feature` is
   minor, and `fix` or `infosec` is patch).
2. To release, push a `v*` tag that matches the draft's version.
3. `release.yml` finds the draft with that tag and publishes it. If there's
   no matching draft, it fails.
4. The same tag starts `images.yml`, which pushes the `X.Y.Z` and `X.Y`
   images.

## Dependency updates

Dependabot opens grouped PRs every week, one for minor and patch updates per
ecosystem. Each PR goes through `images.yml` like any other PR.

| Ecosystem        | Location                          | Updates                                       |
| ---------------- | --------------------------------- | --------------------------------------------- |
| `pip`            | `src/dsv-app`, `src/dsv-pipeline` | `requirements.txt` packages                   |
| `docker`         | `src/dsv-app`, `src/dsv-pipeline` | Dockerfile base images                        |
| `docker-compose` | Repository root                   | Pinned upstream images in both Compose files  |
| `github-actions` | `.github/workflows`               | Action SHA pins and their version comments    |

Major Postgres updates are ignored. Moving to a new major version needs a data
migration, not just a new tag.

## Known limits

These limits follow from the current workflows.

- **No tests in CI.** The `pytest` suites in `tests/`, `src/dsv-app/tests/`,
  and `src/dsv-pipeline/tests/` don't run in any workflow. A green check means
  the images build and pass the vulnerability gate, not that the tests pass.
  Run them locally before you merge.
- **No linting.** No workflow lints Python, shell, or Markdown.
- **One unpinned action.** `release-drafter.yml` uses
  `release-drafter/release-drafter@v7`, a moving tag. Every action in
  `images.yml` is pinned to a commit SHA.
- **amd64 only.** Images are built for `linux/amd64`, the VM's architecture.

## Out of scope

Continuous deployment isn't covered. Deploys are manual: an operator runs
`scripts/deploy.sh` on the VM. For the deploy flow, see
[CI and CD for the Azure VM deployment](../../docs/explanation/azure-vm/ci-cd.md).
