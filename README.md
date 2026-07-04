gi# DineSafeViz

DineSafeViz visualizes data from the
[City of Toronto DineSafe open dataset](https://open.toronto.ca/dataset/dinesafe/),
Toronto Public Health's food safety and inspection program. It demonstrates
end-to-end Infrastructure as Code and container orchestration of a real,
26-year public dataset.

**Stack:** [Docker](https://www.docker.com/) ·
[PostgreSQL](https://www.postgresql.org/) ·
[Grafana](https://grafana.com/) ·
[Terraform](https://www.terraform.io/) ·
[Packer](https://www.packer.io/) ·
[Ansible](https://www.ansible.com/) ·
[Proxmox VE](https://www.proxmox.com/en/proxmox-virtual-environment)

> **This branch** is the on-prem (Proxmox) deployment. An AKS migration is
> in design — see [What's next](#whats-next-aks-migration).

<!-- TODO: live demo URL -->

## Project status

| Component | State |
|---|---|
| Inspection results | Done |
| Inspection analytics dashboard ([Grafana](https://grafana.com/)) | Done |
| AKS deployment | In design |
| Daily data refresh | In progress |
| Monitoring | Planned |


![DineSafeViz home page](docs/img/root-readme/dsv-home-1.png)

## Features

### Inspection results

Browse the complete list of DineSafe inspection results.

![Inspection results page](docs/img/root-readme/inspec-1.png)

### Analytics dashboard

View a stats breakdown of inspection results. Filter by any date range
across over 26 years of data.

![DSV Analytics dashboard](docs/img/root-readme/dsv-dash-1.png)

### Self-hosted

Small footprint. Deploys to a self-hosted Ubuntu VM in a Proxmox environment.

### Infrastructure as Code

Uses [Infrastructure as Code](docs/ref/arch/arch-iac.md) to automate VM
provision and app deployment.

## Architecture

The DineSafeViz application is a Dockerized webapp with a database backend.
It visualizes historic data and updates the dataset daily.

See the [architecture reference](docs/ref/arch/arch-app.md) and
[DevOps reference](docs/ref/arch/README.MD) for details.

### Application architecture

The DineSafeViz app has [three main services](docker-compose.yml) and two
supporting services:

#### Main services

1. **dsv-app:** the user-facing webapp to view inspection data and the metrics dashboard
2. **dsv-db:** stores the City of Toronto DineSafe dataset; a PostgreSQL database
3. **dsv-analytics:** a custom metrics dashboard that visualizes DineSafe data; Grafana-based

#### Supporting services

These are one-off services used for initial setup of a fresh deployment in a VM.

1. **dsv-init-db:** seeds the DB on first run, refreshes recent data on subsequent runs
2. **dsv-init-analytics:** seeds the initial Grafana-based app dashboard

![Architecture overview diagram](docs/img/root-readme/arch-over.drawio.png)

### [Infrastructure as Code](docs/ref/arch/arch-iac.md)

[Terraform](https://www.terraform.io/), [Packer](https://www.packer.io/), and
[Ansible](https://www.ansible.com/) automate:

- provisioning an app VM
- maintaining an app image
- deploying, tearing down, and redeploying the application

### [Information security](docs/ref/arch/arch-security.md)

The app's docker-compose configuration is retrieved from a `.env` file. Secrets
are stored Ansible Vault AES256-encrypted in
[`infra/ansible/vault/secrets.yml`](infra/ansible/vault/secrets.yml) and
injected into the `.env` file at deploy time via Ansible. See
[`infra/ansible/vault/example-secrets.yml`](infra/ansible/vault/example-secrets.yml)
for the template.

### [Monitoring](docs/ref/arch/arch-monitoring.md)

Grafana dashboards will monitor VM health, webapp metrics, and DB metrics.
Monitoring is planned — not yet deployed.

### Further reading

- [Design decisions](docs/ref/arch/arch-design-decision.md)
- [Networking](docs/ref/arch/arch-net.md)
- [CI/CD](docs/ref/arch/arch-ci-cd.md)
- [Disaster recovery](docs/ref/arch/arch-dr.md)
- [Testing](docs/ref/arch/arch-testing.md)

## What's next: AKS migration

The next evolution of DineSafeViz moves the deployment from bare-metal Proxmox
to Azure Kubernetes Service (AKS). See the
[AKS deployment design](docs/superpowers/specs/2026-06-09-aks-deployment-design.md)
and
[AKS deployment plan](docs/superpowers/plans/2026-06-09-aks-deployment.md)
for the current design.

<!-- TODO: export azure.drawio to png -->

## Getting Started

The [install guide](docs/how-to/1-install/README.md) walks through provisioning
infrastructure and deploying the app from scratch. For existing infrastructure,
use the [redeploy guide](docs/how-to/3-redeploy-guide.md).

The app requires database seeding on first run — the install guide covers this.

## Roadmap

[Project Roadmap](https://github.com/users/im-kenough/projects/11)
