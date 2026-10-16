# Continuous integration

This page gives a high-level view of how DineSafeViz checks code before it
merges, builds, scans, and publishes its container images, and tracks
dependencies and releases.

## Overview

The key CI tasks of DineSafeViz are to:
1. Lint, test, and security-check every pull request before it merges
2. Build and scan the owned images on every pull request
3. Publish scanned images to GitHub Container Registry (GHCR) for deploys
4. Rescan published and upstream images for newly disclosed vulnerabilities
5. Keep dependencies current and draft release notes

CI stops at GHCR. It never deploys. `scripts/deploy.sh` pulls a published tag
onto a VM, and an operator runs it.

## Workflows

All automation lives in `.github/`. There are four workflows and one
Dependabot configuration. CodeQL also runs, through GitHub's default setup,
so it has no workflow file.

| File                                    | Triggers                                | Does                                                  |
| --------------------------------------- | --------------------------------------- | ----------------------------------------------------- |
| `.github/workflows/ci.yml`              | Called by `images.yml`                  | Lints, tests, and reviews new dependencies            |
| `.github/workflows/images.yml`          | PR, push to `main`, `v*` tag            | Runs `ci.yml`, then builds, scans, and publishes the owned images; on a `v*` tag, then publishes the matching draft release |
| `.github/workflows/rescan.yml`          | Weekly, manual                          | Rescans the published and pinned upstream images      |
| `.github/workflows/release-drafter.yml` | Push to `main`                          | Rebuilds the draft release notes                      |
| `.github/dependabot.yml`                | Weekly                                  | Opens PRs for outdated dependencies                   |

## Pre-merge checks

Every PR runs a set of free checks. Together they cover linting, tests,
static analysis (SAST), and dependency scanning (SCA). Each one fails the PR
when it finds a problem, so it can be a required check on `main`.

`ci.yml` is a reusable workflow. `images.yml` calls it as its `ci` job (shown
as `CI`), so its checks appear on a PR as `CI / Lint`, `CI / Test`, and
`CI / Dependency review`. The same call runs on pushes to `main` and on `v*`
tags, and the `push` job waits for it.

| Check               | Where                 | Tool                    | Fails on                                           |
| ------------------- | --------------------- | ----------------------- | -------------------------------------------------- |
| `CI / Lint`         | `ci.yml`              | Ruff, shellcheck, yamllint, actionlint, hadolint | Python errors, likely bugs, Bandit security rules, shell bugs, invalid YAML or workflows, Dockerfile warnings |
| `CI / Test`         | `ci.yml`              | pytest                  | Any failing test in the three suites               |
| `CI / Dependency review` | `ci.yml` (PRs only) | Dependency review     | A new dependency with a `high` or `critical` advisory |
| `CodeQL`            | GitHub default setup  | CodeQL                  | Python and Actions alerts, set in the ruleset      |
| `Scan image (<image>)` | `images.yml`       | Trivy                   | Fixable `CRITICAL` vulnerabilities in an image     |

- **Lint:** `ruff.toml` lists the rules explicitly, so a Ruff upgrade can't
  change them. Tests are exempt from the Bandit (`S`) rules, because they run
  local commands and use throwaway passwords. When a finding is a false
  positive in app code, suppress it on that line with `# noqa: <rule>` and a
  comment that says why. `.shellcheckrc` lets shellcheck follow the `lib.sh`
  that the scripts source. `.yamllint` turns off the line-length and
  document-start rules, and skips the Ansible Vault file. hadolint fails on
  warnings and errors. Its info-level notes only appear in the log.
- **Test:** the three suites run separately, because each has its own
  `conftest.py` and helper modules. The database tests start the real Postgres
  image on the runner, the same way they do locally.
- **Tool versions:** Ruff, shellcheck, and yamllint are pinned in
  `requirements-ci.txt`, and CI uses Python 3.14 to match the Dockerfiles.
  hadolint runs through its official action. actionlint runs from its
  official image, pinned by digest. Dependabot doesn't update that image, so
  bump it by hand.

To run the same checks locally:

```bash
pip install -r requirements-ci.txt -r src/dsv-app/requirements.txt \
  -r src/dsv-app/requirements-dev.txt -r src/dsv-pipeline/requirements.txt
ruff check .
git ls-files -z '*.sh' 'tests/fakes/*' | xargs -0 shellcheck
yamllint .
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12
for f in src/*/Dockerfile; do
  docker run --rm -i ghcr.io/hadolint/hadolint:v2.15.1-debian \
    hadolint --failure-threshold warning - < "$f"
done
pytest tests && pytest src/dsv-app/tests && pytest src/dsv-pipeline/tests
```

## Images

`images.yml` builds two images. Upstream images (nginx, Postgres, Grafana, and
cloudflared) are pinned by tag and digest in the Compose files and are never
rebuilt.

| Image                             | Build context      |
| --------------------------------- | ------------------ |
| `ghcr.io/im-kenough/dsv-app`      | `src/dsv-app`      |
| `ghcr.io/im-kenough/dsv-pipeline` | `src/dsv-pipeline` |

`images.yml` has four jobs. Which jobs run depends on the trigger. The
Actions UI shows the display name in parentheses. The job ID before it is
what `needs:` refers to:

| Job           | Runs on                   | Does                                                                 |
| ------------- | ------------------------- | -------------------------------------------------------------------- |
| `ci` (CI)     | PR, push                  | Runs `ci.yml`: lint, tests, and dependency review                    |
| `scan` (Scan image) | PR, push            | Builds each image for `linux/amd64`, scans it with Trivy             |
| `push` (Publish to GHCR) | Push, after `ci` and `scan` pass | Rebuilds from the `scan` job's layer cache, pushes to GHCR    |
| `release` (Publish release) | `v*` tag, after every `push` leg passes | Publishes the draft release that matches the tag          |

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

The `push` job runs only on pushes, and only after `ci` passes and `scan`
passes for both images. A `v*` tag doesn't go through a PR, so this is what
keeps an unlinted or untested commit out of GHCR. Every deployable tag is
immutable. There's no `latest`.

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
06:17 UTC, or on demand, `rescan.yml` runs two jobs. `list-images` builds the
scan list from:

- The `main` tag of both owned images
- The latest published release tag of both owned images
- Every pinned upstream image in `docker-compose.yml` and
  `docker-compose.vm.yml`

`rescan` scans each one and uploads the results to code scanning. It never
fails the run. Read the findings in **Security > Code scanning**.

## Releases

Release notes build up automatically, and a tag publishes them.

1. On every push to `main`, `release-drafter.yml` regenerates
   one draft release. PR labels set the section (for example, `fix` goes to
   **Bug Fixes**) and the next version (`breaking` is major, `feature` is
   minor, and `fix` or `infosec` is patch).
2. To release, push a `v*` tag that matches the draft's version.
3. The tag starts `images.yml`, which pushes the `X.Y.Z` and `X.Y` images.
4. Once both images are pushed, its `release` job finds the draft with that
   tag and publishes it. If CI, the scan, or the push fails, the draft stays
   a draft. If there's no matching draft, the job fails.

## Dependency updates

Dependabot opens grouped PRs every week, one for minor and patch updates per
ecosystem. Each PR goes through `ci.yml` and `images.yml` like any other PR.

| Ecosystem        | Location                          | Updates                                       |
| ---------------- | --------------------------------- | --------------------------------------------- |
| `pip`            | Root, `src/dsv-app`, `src/dsv-pipeline` | `requirements*.txt` packages, including CI lint tools |
| `docker`         | `src/dsv-app`, `src/dsv-pipeline` | Dockerfile base images                        |
| `docker-compose` | Repository root                   | Pinned upstream images in both Compose files  |
| `github-actions` | `.github/workflows`               | Action SHA pins and their version comments    |

Major Postgres updates are ignored. Moving to a new major version needs a data
migration, not just a new tag.

## Known limits

These limits follow from the current workflows.

- **No Markdown linting.** The linters cover Python, shell, YAML, workflows,
  and Dockerfiles only.
- **amd64 only.** Images are built for `linux/amd64`, the VM's architecture.

## Out of scope

Continuous deployment isn't covered. Deploys are manual: an operator runs
`scripts/deploy.sh` on the VM. For the deploy flow, see
[CI and CD for the Azure VM deployment](../../docs/explanation/azure-vm/ci-cd.md).
