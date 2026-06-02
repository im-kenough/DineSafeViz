# DineSafeViz

DineSafeViz visualizes data from DineSafe, Toronto Public Health's food
safety and inspection program.

It's a selfhosted containerized webapp that publishes and visualizes 26+ years of inspection results.

![DineSafeViz home page](docs/img/root-readme/dsv-home-1.png)

## Features

### Inspection results

Browse the complete list of DineSafe inspection results.

![Inspection results page](docs/img/root-readme/inspec-1.png)

### Analytics dashboard

View a stats breakdown of inspection results. Filter by any date range
across over 26 years of data.

![DSV Analytics dashboard](docs/img/root-readme/dsv-dash-1.png)

### Selfhosted

Small foot print. Deploys to a selfhosted Ubuntu VM in a Proxmox environment.

### Infrastructure as Code

Uses [Infrastructure as Code](docs/ref/arch/arch-iac.md) to automate VM provision and app deployment

## Architecture

The DineSafeViz application is a Dockerized webapp with a database backend. It visualizes historic data and updates the dataset daily. 

> [!NOTE]
> Data update feature Coming Soon (™️)

See the
[architecture reference](docs/ref/arch/arch-app.md) and
[DevOps reference](docs/ref/arch/README.MD) for details.

### Application Architecture

The DineSafeViz app has [three main services](docker-compose.yml) and two supporting services:

#### Main services
1. dsv-app: the user facing webapp to view inspection data and metrics dashboard
2. dsv-db: stores the City of Toronto DineSafe dataset; a PostgreSQL database 
3. dsv-analytics: a custom metrics dashboard that visualises DineSafe data; Grafana based.

#### Supporting services

These are one off services used for initial setup of fresh deployment in a VM.

1. dsv-init-db: seeds the DB on first run, refreshes recent data on subsequent runs.
2. dsv-init-analytics: seeds the initial Grafana based app dashboard

![Architecture overview diagram](docs/img/root-readme/arch-over.drawio.png)

### [Infrastructure as Code](docs/ref/arch/arch-iac.md)

Terraform, Packer and Ansible are used for Infrastructure as Code tools to automatically:
- provision an app VM
- maintain an app image
- deploy, teardown and redeploy an application

### [Information security](docs/ref/arch/arch-security.md)

The app's docker-compose configuration are retrieved from a .env file. Secrets are stored in [secrets.yml](DineSafeViz/infra/ansible/vault/secrets.yml) and are injected to the .env file during deployment via IAC.

### [Monitoring](docs/ref/arch/arch-monitoring.md)

Coming Soon (™️)

Grafana dashboards monitors: the VM health, webapp metrics, db metrics
docs/ref/arch/arch-monitoring.md


## Getting Started

### Installing from scratch

First we need to
To deploy the app:
- install the infrastructure
- install the app

### Deployment

Once the infrastrure is already provisioned you can redeploy the app.

## Roadmap

[Coming Soon](https://github.com/users/im-kenough/projects/11) (™️)


## Evolution

Watch how DineSafeViz evolved over time:

v x.y.z - Dockerized app on self hosted VM. Orchestrated with IAC.