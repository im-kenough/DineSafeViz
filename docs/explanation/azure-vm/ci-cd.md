# CI and CD for the Azure VM deployment

This document explains how a code change becomes a running container on the
stg or prod VM. It covers the workflows, how images are tagged, how
dependencies and vulnerabilities are tracked, and worked examples of the
common tasks.

<!-- prettier-ignore -->
> [!NOTE]
> This describes the target state for the Azure VM deployment. It isn't built
> yet. In Phase 1, deploys are manual over SSH. Phase 2 runs the same
> `deploy.sh` from GitHub Actions.

## Pipeline at a glance

CI builds, scans, and publishes images. CD pulls a specific image tag onto a
VM. The two meet at GHCR.

```mermaid
flowchart LR
    pr[Pull request] -->|lint + test + build + scan, no push| ci[ci.yml]
    main[Merge to main] -->|lint + test + build + scan + push| ghcr[(GHCR)]
    tag[Push tag v*] -->|lint + test + build + scan + push| ghcr
    ghcr -->|"sha-abc1234"| stg["vm-dsv-stg01<br/>deploy.sh stg main"]
    ghcr -->|"0.5.0"| prod["vm-dsv-prod01<br/>deploy.sh prod v0.5.0"]
```

The rule is simple: `main` goes to stg, and `v*` tags go to prod. The same rule
appears in the image tags, in `deploy.sh`, and in the Phase 2 GitHub
Environment protections described in
[Identity and access management](../../ref/iam.md).

## Workflows

The repository has these automation pieces:

| File                                  | Trigger                       | What it does                                                    |
| ------------------------------------- | ----------------------------- | --------------------------------------------------------------- |
| `.github/workflows/ci.yml`            | PR, push to `main`, `v*` tag  | Lints, tests, reviews new dependencies, builds and scans the owned images, (except on PRs) pushes them once everything passes, and on a `v*` tag publishes the matching draft release after the push |
| `.github/workflows/rescan-images.yml` | Weekly, manual                | Rescans the published and pinned upstream images                |
| `.github/workflows/code-scanning.yml` | PR, push to `main`, weekly    | Runs CodeQL and reports Trivy IaC findings                      |
| `.github/workflows/release-drafter.yml` | Push to `main`              | Keeps the draft release notes up to date                        |
| `.github/dependabot.yml`              | Weekly schedule               | Opens PRs for outdated dependencies                             |

`ci.yml` builds two images. Upstream images (nginx, Postgres, Grafana,
curl, and cloudflared) are pulled by pinned tag and aren't rebuilt.

| Image                             | Source             |
| --------------------------------- | ------------------ |
| `ghcr.io/im-kenough/dsv-app`      | `src/dsv-app`      |
| `ghcr.io/im-kenough/dsv-pipeline` | `src/dsv-pipeline` |

## Image tags

Every deployable tag is immutable, so the code on the VM and the image it runs
always match, and rolling back means deploying an older tag.

| Trigger        | Tags pushed           | Deployed with              |
| -------------- | --------------------- | -------------------------- |
| Pull request   | None (build only)     | Not deployed               |
| Push to `main` | `main`, `sha-abc1234` | `deploy.sh stg main`       |
| Tag `v0.5.0`   | `0.5.0`, `0.5`        | `deploy.sh prod v0.5.0`    |

There's no `latest` tag. `deploy.sh stg main` resolves `main` to its commit
and pulls the matching `sha-` tag, never the moving `main` tag.

## Dependency updates and vulnerability scanning

Three free tools keep dependencies current and flag known vulnerabilities.

- **Dependabot version updates** open weekly PRs for each ecosystem:

  | Ecosystem        | Location                          | Updates                                          |
  | ---------------- | --------------------------------- | ------------------------------------------------ |
  | `github-actions` | `.github/workflows`               | Action SHA pins and their version comments       |
  | `docker`         | `src/dsv-app`, `src/dsv-pipeline` | Dockerfile base images                           |
  | `docker-compose` | Repository root                   | nginx, Postgres, Grafana, curl, cloudflared tags |
  | `pip`            | Root, `src/dsv-app`, `src/dsv-pipeline` | `requirements*.txt` packages             |

  Minor and patch updates are grouped into one PR per ecosystem. Major
  Postgres updates are ignored, because moving from 17 to 18 needs a data
  migration, not just a new tag. GitHub doesn't document whether the
  `docker-compose` ecosystem reads override files, so watch for a
  cloudflared PR. If none arrives, the weekly rescan still flags
  vulnerabilities in the pinned cloudflared tag, and you update it by hand.

- **Dependabot alerts and security updates** are turned on in the repository
  settings. They open PRs when a dependency has a published advisory, without
  waiting for the weekly schedule.

- **Trivy image scanning** runs in `ci.yml`. Each owned image is built
  locally, scanned, and only pushed if the scan passes. On pushes, results go
  to the repository's **Security > Code scanning** page as SARIF; on pull
  requests, the scan prints a table in the job log. A weekly scheduled run
  of `rescan-images.yml` rescans the deployed tags and the pinned upstream
  images, because new vulnerabilities are published after an image is built.

  | Setting          | Value                                       |
  | ---------------- | ------------------------------------------- |
  | Blocks the push  | `CRITICAL` vulnerabilities that have a fix  |
  | Reported only    | `HIGH` and below, and anything without a fix |

Code scanning and Dependabot are free for public repositories. All actions are
pinned to full commit SHAs, and Dependabot keeps those pins current.

## Examples

The following examples show the common tasks end to end. In Phase 1, the
deploy commands run over SSH on the VM.

### Open a pull request

When you open a PR, `ci.yml` lints and tests the code, reviews new
dependencies, and builds and scans both images, but doesn't push anything. A
red check means a lint or test failure, a new vulnerable dependency, a Dockerfile that
no longer builds, or an image with a fixable critical vulnerability. For the
full list of checks, see
[Pre-merge checks](../../../docs-new/ref/4-ci.md#pre-merge-checks).

```bash
git switch -c fix-map-legend
git commit -am "fix(app): correct map legend colors"
git push -u origin fix-map-legend
gh pr create --fill
```

### Deploy to stg

After the PR merges, `ci.yml` pushes `sha-<commit>` for the new `main`.
When the workflow is green, deploy that commit to stg:

```bash
gh run watch                       # wait for ci.yml on main
ssh dsv-stg                        # vm-dsv-stg01
cd ~/DineSafeViz && ./scripts/deploy.sh stg main
```

`deploy.sh` fails before changing anything if the matching `sha-` image
doesn't exist yet.

### Release to prod

A release is a `v*` tag on a commit that's already been checked on stg.
Pushing the tag builds the `0.5.0` images, then publishes the draft release
once both are in GHCR. If lint, tests, or the scan fail, the draft stays a draft.

```bash
git switch main && git pull
git tag v0.5.0 && git push origin v0.5.0
gh run watch                       # wait for ci.yml on v0.5.0
```

Then, from your workstation as `dsv-ops01`, take a pre-deploy snapshot of the
prod OS disk. Snapshots go in `rg-dsv-prod01-snapshots`, which has no lock,
because the lock on `rg-dsv-prod01` would stop you deleting old ones. Set
`SUB_ID` to the ID of subscription `sub-dsv-prod01` first:

```bash
DISK=$(az vm show -g rg-dsv-prod01 -n vm-dsv-prod01 \
  --subscription "$SUB_ID" --query storageProfile.osDisk.managedDisk.id -o tsv)
az snapshot create -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" \
  -n "snap-dsv-prod01-v0.5.0-$(date +%Y%m%d)" --source "$DISK" --incremental true
```

Keep the newest three snapshots and delete the rest. Then deploy:

```bash
ssh dsv-prod                       # vm-dsv-prod01
cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.5.0
```

### Roll back prod

If a release misbehaves, deploy the previous tag. The images and the Git tag
both still exist, so this is the same command with an older version:

```bash
ssh dsv-prod
cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.4.0
```

If the VM itself is damaged, restore the pre-deploy snapshot instead.

### Handle a Dependabot PR

Treat a Dependabot PR like any other PR: let `ci.yml` check it,
check the release notes for breaking changes, then merge and deploy to stg.
For Grafana and nginx updates, check `/analytics/` and the map on stg before
the next release. A Grafana update also changes the bundled PostgreSQL plugin.
Before you merge one, confirm that the new image still bundles it, as
described in
[Grafana: the bundled PostgreSQL plugin](../grafana-postgres-plugin.md#how-the-plugin-gets-updated).

### Fix a failed scan

When Trivy blocks a push, open **Security > Code scanning**, find the
vulnerability, and check its fixed version. Most fixes are one of these:

- Merge the pending Dependabot PR for the base image or package.
- Bump the package in `requirements.txt` to the fixed version.
- Rebuild without changes, if the fix is already in the base image's tag.

## Next steps

In Phase 2, a deploy job in GitHub Actions replaces the manual SSH step. It
signs in to Azure with the environment's deploy identity through OIDC and runs
`deploy.sh` on the VM with Run Command. Prod deploys still need a reviewer's
approval in the `prod` GitHub Environment.
