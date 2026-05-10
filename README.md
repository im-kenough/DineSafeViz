# DineSafeViz

A dockerized web app that visualizes data from Toronto Public Health's food
safety and inspection program, DineSafe. DineSafe publishes restaurant
inspection results as open data, with over 26 years of history.

![DineSafeViz home page](docs/img/root-readme/dsv-home-1.png)

## Features

### Inspection results

Browse the complete list of DineSafe inspection results.

![Inspection results page](docs/img/root-readme/inspec-1.png)

### Analytics dashboard

View a stats breakdown of inspection results. Filter by any date range
across over 26 years of data.

![DSV Analytics dashboard](docs/img/root-readme/dsv-dash-1.png)

## Tech stack

DineSafeViz runs as a Docker Compose stack. See the
[architecture reference](docs/ref/arch.md) and
[DevOps reference](docs/ref/devops.md) for details.

## Architecture

Four services work together: a Flask web app, a PostgreSQL database, a
database initializer that seeds data from the Toronto Open Data API, and a
Grafana analytics dashboard.

![Architecture overview diagram](docs/img/root-readme/arch-over.drawio.png)

## Documentation

- [Installation guide](docs/how-to/1-install-guide.md) — first-time setup
- [Deployment guide](docs/how-to/3-deploy-guide.md) — deploy or redeploy
  after a change
