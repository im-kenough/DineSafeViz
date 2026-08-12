# Continuous integration / continuous deployment architecture

This document describes the CI/CD architecture of the DineSafeViz
application. As of May 2026, the project has **release automation and
dependency management** but **no continuous integration pipelines**
(no automated build, test, or lint steps).

## Continuous integration

There are currently no CI workflows. Pull requests merge without
automated checks. Identified gaps:

- **No build verification** — no workflow confirms that
  `docker compose build` succeeds on PR branches.
- **No automated tests** — no unit, integration, or smoke test
  suites run in CI.
- **No linting or static analysis** — no pre-commit hooks or
  workflow-based linters.
- **No container image registry** — `docker compose build` builds
  images locally on the deployment target, and the pipeline doesn't
  push them to a registry.

## Dependency management (Dependabot)

Dependabot opens weekly PRs against `main` to bump outdated
dependencies. Configuration lives in `.github/dependabot.yml`.

| Ecosystem        | Directory       | Schedule |
|------------------|-----------------|----------|
| pip (Python)     | `/src/dsv-app`  | Weekly   |
| Docker           | `/src/dsv-app`  | Weekly   |
| Docker           | `/src/dsv-db`   | Weekly   |
| GitHub Actions   | `/`             | Weekly   |

Because there are no CI checks, Dependabot PRs rely entirely on
manual review before merging.

## Release process

Releases follow a two-stage, label-driven workflow powered by
GitHub Actions and the
[release-drafter](https://github.com/release-drafter/release-drafter)
action.

### Stage 1 — Draft release (automatic)

**Workflow:** `.github/workflows/release-drafter.yml`
**Triggers:** push to `main`, PR opened/reopened/synchronized.

On every trigger, the release-drafter action rebuilds a single draft
GitHub Release. It:

1. Collects all PRs merged since the last published tag.
2. Categorizes them by PR label using the mapping in
   `.github/release-drafter.yml`.
3. Resolves the next semantic version based on label types:
   - `major` / `breaking` — bumps the major version.
   - `feature` / `enhancement` — bumps the minor version.
   - `bug` / `fix` / `infosec` — bumps the patch version.
4. Generates the draft title (`v<version>`), tag, and body from
   the template.

The draft body includes links to the install guide, deployment guide,
administration guide, PIV guide, and a rollback section (TBD).

### Stage 2 — Publish release (manual trigger)

**Workflow:** `.github/workflows/release.yml`
**Triggers:** push of a Git tag matching `v*`.

When a maintainer pushes a version tag (for example, `git tag v0.3.0
&& git push origin v0.3.0`), this workflow:

1. Queries the GitHub API for a draft release whose `tag_name` matches
   the pushed tag.
2. If found, patches the release to `draft: false`, publishing it.
3. If no matching draft exists, the workflow fails with an error.

### Label-to-section mapping

PR labels control both the changelog section and the semver bump.
`.github/release-drafter.yml` defines the full mapping:

| Section heading          | Labels                                          |
|--------------------------|--------------------------------------------------|
| Security                 | `infosec`                                        |
| Features                 | `feature`, `enhancement`                         |
| UI                       | `ui`                                             |
| Bug Fixes                | `bug`, `fix`                                     |
| Infrastructure           | `infra`, `iac`, `ops`, `dr`, `db`                |
| CI/CD                    | `ci-cd`, `github_actions`                        |
| Build and Dependencies   | `build`, `dependencies`, `python`, `docker`      |
| Documentation            | `documentation`                                  |
| Maintenance              | `refactor`, `chore`                              |

## Deployment

The IaC toolchain in `infra/` handles deployment outside of GitHub
Actions. The `infra/Makefile` orchestrates Packer image baking,
Terraform VM provisioning, and Ansible-based app deployment. See
[IaC architecture](4-infrastructure-as-code.md) for details.

There is no continuous deployment. You deploy releases manually using
`make deploy-app` (or `make up` for a full-stack provision).