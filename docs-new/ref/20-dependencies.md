# Dependencies

This project aims to use the latest stable LTS (Long Term Support) version of
dependencies. Dependabot keeps them current, and `.github/dependabot.yml`
enforces the rules on this page.

Dependencies and software versions to standardize on:

- Python 3.14.\* (patch updates only)
- PostgreSQL 18.x (major upgrades need a data migration)
- Alpine 3.24 (the base of the Python and PostgreSQL images)
- nginx 1.31.x
- Grafana 13.x
- cloudflared (calendar versioned, 2026.x)
- Terraform 1.16, `azurerm` ~> 5.10, `azuread` ~> 3.10, `bpg/proxmox`
- CI lint tools in `requirements-ci.txt`: ruff, zizmor, actionlint-py,
  shellcheck-py, yamllint
- Pre-commit hooks in `.pre-commit-config.yaml`: gitleaks, pre-commit-hooks

## Update rules

Dependabot opens one grouped pull request per ecosystem each week and waits 7
days after a release. It ignores these updates, so you must make them by hand:

- Python major and minor versions
- PostgreSQL, Grafana, and nginx major versions
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
