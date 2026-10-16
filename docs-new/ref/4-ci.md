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
Dependabot configuration. Each file name matches its workflow name in the
Actions tab. CodeQL runs from `code-scanning.yml`, so GitHub's
CodeQL default setup must stay off. While it's on, GitHub rejects the
workflow's uploads.

| File                                    | Name            | Triggers                           | Does                                                  |
| --------------------------------------- | --------------- | ---------------------------------- | ----------------------------------------------------- |
| `.github/workflows/ci.yml`              | CI              | PR, push to `main`, `v*` tag       | Lints, tests, reviews new dependencies, and builds and scans the owned images; on a push, publishes them; on a `v*` tag, then publishes the matching draft release |
| `.github/workflows/code-scanning.yml`   | Code scanning   | PR, push to `main`, weekly, manual | Runs CodeQL and reports every Trivy IaC finding       |
| `.github/workflows/rescan-images.yml`   | Rescan images   | Weekly, manual                     | Rescans the published and pinned upstream images      |
| `.github/workflows/release-drafter.yml` | Release drafter | Push to `main`                     | Rebuilds the draft release notes                      |
| `.github/dependabot.yml`                | n/a             | Weekly                             | Opens PRs for outdated dependencies                   |

## Pre-merge checks

Every PR runs a set of free checks. Together they cover linting, tests,
static analysis (SAST), and dependency scanning (SCA). Each one fails the PR
when it finds a problem, so it can be a required check on `main`.

A PR lists each check as `<workflow> / <job>`, for example `CI / Lint`. The
ruleset requires the check by its job name alone, so renaming a job in
`ci.yml` means updating the `force-pr-force-checks` ruleset in the same PR.
`Lint`, `Test`, `Dependency review`, and both `Build and scan` legs are
required.

| Check                         | Where               | Tool                    | Fails on                                           |
| ----------------------------- | ------------------- | ----------------------- | -------------------------------------------------- |
| `Lint`                        | `ci.yml`            | Ruff, shellcheck, yamllint, actionlint, zizmor, hadolint, gitleaks, Trivy config | Python errors, likely bugs, Bandit security rules, shell bugs, invalid YAML or workflows, insecure workflows, Dockerfile warnings, secrets in git history, `CRITICAL` IaC misconfigurations |
| `Test`                        | `ci.yml`            | pytest                  | Any failing test in the three suites               |
| `Dependency review`           | `ci.yml` (PRs only) | Dependency review       | A new dependency with a `high` or `critical` advisory |
| `Build and scan (<image>)`    | `ci.yml`            | Docker Buildx, Trivy    | A Dockerfile that doesn't build, or fixable `CRITICAL` vulnerabilities in an image |
| `CodeQL (<language>)`         | `code-scanning.yml` | CodeQL                  | Python and Actions alerts, set in the ruleset      |
| `Trivy IaC`                   | `code-scanning.yml` | Trivy config            | Never fails; reports every severity                |

- **Lint:** `ruff.toml` lists the rules explicitly, so a Ruff upgrade can't
  change them. Tests are exempt from the Bandit (`S`) rules, because they run
  local commands and use throwaway passwords. When a finding is a false
  positive in app code, suppress it on that line with `# noqa: <rule>` and a
  comment that says why. `.shellcheckrc` lets shellcheck follow the `lib.sh`
  that the scripts source. `.yamllint` turns off the line-length and
  document-start rules, and skips the Ansible Vault file. hadolint fails on
  warnings and errors. Its info-level notes only appear in the log.
- **Secrets:** gitleaks scans the full git history, not just the PR's diff.
  Reviewed false positives are fingerprinted in `.gitleaksignore`. The same
  scan runs as a local pre-commit hook after `pre-commit install`.
- **Workflows:** zizmor audits the workflows and `dependabot.yml` for
  security issues. No findings are accepted. To accept one, add a
  `.github/zizmor.yml` with the reason. `ci.yml` doesn't use the pip cache,
  because zizmor flags caches in a workflow that publishes.
- **IaC:** Trivy config fails on `CRITICAL` Terraform and Dockerfile
  misconfigurations. `code-scanning.yml` reports every severity to
  **Security > Code scanning**.
- **Test:** the three suites run separately, because each has its own
  `conftest.py` and helper modules. The database tests start the real Postgres
  image on the runner, the same way they do locally.
- **Tool versions:** Ruff, shellcheck, yamllint, actionlint, and zizmor are
  pinned in `requirements-ci.txt`, and CI uses Python 3.14 to match the
  Dockerfiles. hadolint and gitleaks run from their official images, pinned
  by digest. Dependabot doesn't update those images, so bump them by hand.

To run the same checks locally:

```bash
pip install -r requirements-ci.txt -r src/dsv-app/requirements.txt \
  -r src/dsv-app/requirements-dev.txt -r src/dsv-pipeline/requirements.txt
ruff check .
git ls-files -z '*.sh' 'tests/fakes/*' | xargs -0 shellcheck
yamllint .
actionlint
zizmor .
docker run --rm -v "$PWD:/repo" -w /repo ghcr.io/gitleaks/gitleaks:v8.30.1 \
  git --redact .
docker run --rm -v "$PWD:/repo" -w /repo aquasec/trivy:0.76.0 \
  config --severity CRITICAL --exit-code 1 .
for f in src/*/Dockerfile; do
  docker run --rm -i ghcr.io/hadolint/hadolint:v2.15.1-debian \
    hadolint --failure-threshold warning - < "$f"
done
pytest tests && pytest src/dsv-app/tests && pytest src/dsv-pipeline/tests
```

## Images

`ci.yml` builds two images. Upstream images (nginx, Postgres, Grafana, and
cloudflared) are pinned by tag and digest in the Compose files and are never
rebuilt.

| Image                             | Build context      |
| --------------------------------- | ------------------ |
| `ghcr.io/im-kenough/dsv-app`      | `src/dsv-app`      |
| `ghcr.io/im-kenough/dsv-pipeline` | `src/dsv-pipeline` |

`ci.yml` has six jobs. Which jobs run depends on the trigger. The Actions UI
shows the display name in parentheses. The job ID before it is what `needs:`
refers to:

| Job                                   | Runs on                                    | Does                                                         |
| ------------------------------------- | ------------------------------------------ | ------------------------------------------------------------ |
| `lint` (Lint)                         | PR, push                                   | Runs the linters and security checks                         |
| `test` (Test)                         | PR, push                                   | Runs the three pytest suites                                 |
| `dependency-review` (Dependency review) | PR                                       | Reviews new dependencies                                     |
| `build-scan` (Build and scan)         | PR, push                                   | Builds each image for `linux/amd64`, scans it with Trivy     |
| `publish-images` (Publish images)     | Push, after `lint`, `test`, and `build-scan` pass | Rebuilds from the `build-scan` layer cache, pushes to GHCR |
| `publish-release` (Publish release)   | `v*` tag, after both `publish-images` legs pass | Publishes the draft release that matches the tag        |

On a PR, the two publish jobs show as skipped.

### Build and scan: gate every build

The `build-scan` job builds each image locally and runs Trivy against it before
anything is pushed.

- **Gate:** the job fails on `CRITICAL` vulnerabilities that have a fix.
  `HIGH` and below, and anything without a fix, never fail the build.
- **Report:** on pushes, a second Trivy pass uploads every severity as SARIF
  to **Security > Code scanning**. On PRs, only the gate's table appears, in
  the job log.
- **Cache:** layers go to the GitHub Actions cache, scoped per image. The
  `publish-images` job reuses them, so the image it pushes is the one that was scanned.

### Publish: push deployable tags

The `publish-images` job runs only on pushes, and only after `lint`, `test`,
and `build-scan` pass for both images. A `v*` tag doesn't go through a PR, so this is what
keeps an unlinted or untested commit out of GHCR. Every deployable tag is
immutable. There's no `latest`.

| Trigger        | Tags pushed           | Deployed with           |
| -------------- | --------------------- | ----------------------- |
| Pull request   | None                  | Not deployed            |
| Push to `main` | `main`, `sha-<7>`     | `deploy.sh stg main`    |
| Tag `v0.5.0`   | `0.5.0`, `0.5`        | `deploy.sh prod v0.5.0` |

`deploy.sh stg main` resolves `origin/main` to a commit and pulls the matching
`sha-` tag, never the moving `main` tag. Before it changes anything, it
checks that both images exist in GHCR. If `ci.yml` hasn't finished, the
deploy stops.

### Rescan: catch new vulnerabilities

New vulnerabilities are published after an image is built. Every Monday at
06:17 UTC, or on demand, `rescan-images.yml` runs two jobs. `list-images`
builds the scan list from:

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
3. The tag starts `ci.yml`, which pushes the `X.Y.Z` and `X.Y` images.
4. Once both images are pushed, its `publish-release` job finds the draft
   with that tag and publishes it. If lint, tests, the scan, or the push
   fails, the draft stays a draft. If there's no matching draft, the job fails.

## Dependency updates

Dependabot opens grouped PRs every week, one for minor and patch updates per
ecosystem. Each PR goes through `ci.yml` like any other PR.

| Ecosystem        | Location                          | Updates                                       |
| ---------------- | --------------------------------- | --------------------------------------------- |
| `pip`            | Root, `src/dsv-app`, `src/dsv-pipeline` | `requirements*.txt` packages, including CI lint tools |
| `docker`         | `src/dsv-app`, `src/dsv-pipeline` | Dockerfile base images                        |
| `docker-compose` | Repository root                   | Pinned upstream images in both Compose files  |
| `github-actions` | `.github/workflows`               | Action SHA pins and their version comments    |

Major Postgres updates are ignored. Moving to a new major version needs a data
migration, not just a new tag.

Every ecosystem has a 7-day cooldown: Dependabot waits a week after a release
before proposing it, so a hijacked version is likely pulled first. Security
updates ignore the cooldown.

## Known limits

These limits follow from the current workflows.

- **No Markdown linting.** The linters cover Python, shell, YAML, workflows,
  and Dockerfiles only.
- **amd64 only.** Images are built for `linux/amd64`, the VM's architecture.

## Out of scope

Continuous deployment isn't covered. Deploys are manual: an operator runs
`scripts/deploy.sh` on the VM. For the deploy flow, see
[CI and CD for the Azure VM deployment](../../docs/explanation/azure-vm/ci-cd.md).
For the security controls at each stage, see [DevSecOps](5-devsecops.md).
