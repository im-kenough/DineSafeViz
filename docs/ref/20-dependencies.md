# Dependencies

This page is the source of truth for the versions DineSafeViz standardizes on
and where its container images come from. Dependabot keeps dependencies
current, and `.github/dependabot.yml` enforces the rules on this page. Other
docs and config comments link here instead of repeating versions.

## Version standards

Use the latest stable or LTS (long-term support) release of each dependency,
within these lines:

- Python 3.14.\* (patch updates only)
- PostgreSQL 18.x (major upgrades need a data migration)
- Alpine 3.24 (the base of the Python, PostgreSQL, nginx, and Grafana images)
- nginx 1.30.x, the stable branch. Don't use the mainline branch, which has
  odd minor versions such as 1.31.
- Grafana 13.x
- cloudflared (calendar versioned, 2026.x)
- Terraform 1.16, `azurerm` ~> 5.10, `azuread` ~> 3.10, `bpg/proxmox`
- CI lint tools in `requirements-ci.txt`: ruff, zizmor, actionlint-py,
  shellcheck-py, yamllint
- Pre-commit hooks in `.pre-commit-config.yaml`: gitleaks, pre-commit-hooks

## Container images

Pull images only from the official vendor. The Compose files and Dockerfiles
pin each image by tag and digest. Use these pages to find new releases and
tags.

| Image                    | Used by                              | Releases                                                                                                  | Tags                                                                     |
| ------------------------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `cloudflare/cloudflared` | `dsv-tunnel`                         | [cloudflared releases](https://github.com/cloudflare/cloudflared/releases)                                | [cloudflared tags](https://hub.docker.com/r/cloudflare/cloudflared/tags) |
| `nginx`                  | `dsv-nginx`                          | [nginx downloads](https://nginx.org/en/download.html)                                                     | [nginx tags](https://hub.docker.com/_/nginx/tags)                        |
| `postgres`               | `dsv-db`                             | [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/), [PostgreSQL end of life](https://endoflife.date/postgresql) | [postgres tags](https://hub.docker.com/_/postgres/tags)                  |
| `grafana/grafana`        | `dsv-analytics`                      | [Grafana releases](https://github.com/grafana/grafana/releases)                                           | [Grafana tags](https://hub.docker.com/r/grafana/grafana/tags)            |
| `python`                 | `dsv-app` and `dsv-pipeline` (base) | [Python downloads](https://www.python.org/downloads/)                                                     | [python tags](https://hub.docker.com/_/python/tags)                      |

`curlimages/curl` isn't part of the stack. `infra/az/init-setup-vm.sh` uses
it once, unpinned, to query the VM's metadata service, so Dependabot doesn't
track it.

## Base operating systems

Most images use the same Alpine release, so an Alpine end of life affects
several services at once. Check the base when you bump an image.

- Alpine 3.24: `python`, `postgres`, `nginx`, and `grafana/grafana`. See
  [Alpine releases](https://alpinelinux.org/releases/).
- Debian 13 (distroless): `cloudflare/cloudflared`. See
  [Debian releases](https://www.debian.org/releases/).

## Update rules

Dependabot opens one grouped pull request per ecosystem each week and waits 7
days after a release. Security updates skip the wait. It ignores these updates,
so you must make them by hand:

- Python major and minor versions
- PostgreSQL, Grafana, and nginx major versions
- nginx minor versions, because the next minor version is mainline. Move to
  the next stable branch (the next even minor version) by hand.
- Terraform provider major versions

## Secrets in Terraform and config files

Terraform state, variable, and plan files can hold secret values. Don't commit
them. Two layers enforce this:

- `.gitignore` excludes `*.tfstate*`, `terraform.tfvars`, `*.secret.tfvars`,
  `*.auto.tfvars`, `*.tfplan`, crash logs, and override files. The
  `infra/terraform/envs/<env>/*.tfvars` files hold only non-secret settings, so
  they're committed along with `*.tfvars.example` files.
- The pre-commit hooks run gitleaks, `detect-private-key`, and a local hook
  that blocks those file types even when someone force-adds them. Put secret
  values in a `<layer>.secret.tfvars` file, never in a committed `.tfvars`.

Mark every Terraform variable that holds a secret with `sensitive = true`.
