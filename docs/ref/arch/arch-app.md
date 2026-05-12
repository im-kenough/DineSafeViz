# Application Architecture 

This document describes the architecture of the DineSaveViz application

DineSafeViz runs as five Docker Compose services on a shared network. Four
services are long-running; two are one-shot helpers that exit after
completing their startup tasks.

![Architecture overview](../img/root-readme/arch-over.drawio.png)


## Web app

Flask serves web pages where users can view a list of health and safety inspections.

They can also access an analytics dashboard breaking down the stats.


## DineSafeViz Analytics Dashboard

The DineSafeViz Analytics Dashboard breaks down the dataset and visualises them in a grafana dashboard

### Database

The webapp and analytics services pulls data from a postgresql db.

A bulk dataload is performed when the app is first created. Periodic updates will 

------------


## Services

The services and their relationships are described below.

- **`dsv-db`** — `postgres:17.9`. Stores all DineSafe inspection data in a
  single `inspections` table. Data persists in a named volume
  (`dsv-db-data`). Exposes a healthcheck used by dependent services.

- **`dsv-app`** — `python:3.14-slim`. Runs the Flask web app on port 5000.
  Connects to `dsv-db` for inspection queries and reverse-proxies the
  Grafana dashboard at `/analytics/`. Starts after `dsv-db` is healthy and
  `dsv-analytics` has started.

- **`dsv-analytics`** — `grafana/grafana:11.6.0`. Serves a pre-provisioned
  Grafana dashboard on port 3000. Uses `dsv-db` as its data source.
  Accessible directly at `localhost:3000/analytics/` or through the Flask
  proxy at `localhost:5000/analytics/`. Dashboard state persists in a named
  volume (`dsv-analytics-data`).

- **`dsv-init-db`** — One-shot Python container (`python:3.14-slim`). Runs
  `refresh.py` on startup. Seeds the database on first run; refreshes recent
  data on subsequent runs. Exits after completion.

- **`dsv-init-analytics`** — One-shot curl container. Waits for Grafana to
  become healthy, then grants Viewer-role access to the provisioned
  dashboard. Required because Grafana 11 RBAC does not grant anonymous
  viewers dashboard access by default.

## Data ingestion

Data loading is handled by `src/dsv-db/refresh.py`, which runs as
`dsv-init-db` on each `docker compose up`. It detects whether the table is
empty and takes one of two paths:

- **Seed (empty table):** Downloads the historical ZIP archive (2001–2022
  annual CSVs) and the current CSV (2023–present) from Toronto Open Data,
  then inserts both into the `inspections` table.

- **Refresh (table has data):** Downloads only the current CSV, derives the
  earliest date in that file, deletes all rows at or after that date, and
  inserts the fresh rows — all within a single transaction.

For details on the data sources and schema, see [data](data.md).

## Web app

The Flask app at `src/dsv-app/app.py` serves four pages and one proxy
endpoint:

| Route | Description |
|---|---|
| `GET /` | Home page with summary statistics (total inspections, years of data) |
| `GET /inspections` | Inspection log, filterable by year and quarter |
| `GET /dashboard` | Embeds the Grafana dashboard via iframe |
| `GET /info` | Background on the DineSafe dataset |
| `/analytics/<path>` | Reverse proxy to the internal Grafana container |

Inspections are grouped by date and sorted by severity within each day
(Crucial → Significant → Minor → no infraction). Year/quarter navigation
covers 2001 to the present.

## Data model

One table: `inspections`. See [data](data.md).

## File layout

```text
DineSafeViz/
├── docker-compose.yml
└── src/
    ├── dsv-db/
    │   ├── Dockerfile
    │   ├── init.sql              (creates table schema on first postgres start)
    │   ├── refresh.py            (data seeding and daily refresh)
    │   ├── requirements.txt
    │   └── tests/
    ├── dsv-analytics/
    │   └── provisioning/
    │       ├── dashboards/       (dashboard.yml, dinesafe.json)
    │       └── datasources/      (datasource.yml)
    └── dsv-app/
        ├── Dockerfile
        ├── app.py
        ├── requirements.txt
        ├── requirements-dev.txt
        ├── VERSION.txt
        ├── static/
        │   ├── style.css
        │   └── favicon/
        ├── templates/
        │   ├── base.html
        │   ├── home.html
        │   ├── index.html
        │   ├── dashboard.html
        │   └── info.html
        └── tests/
```

## Configuration

All services are configured via environment variables, typically set in a
`.env` file. See the `.env.example` file for the full list.

| Variable | Used by | Default | Description |
|---|---|---|---|
| `DSV_DB_HOST` | app, init-db, analytics | `dsv-db` | Postgres hostname |
| `DSV_DB_PORT` | app, init-db, analytics | `5432` | Postgres port |
| `DSV_DB_NAME` | app, init-db, analytics | `dinesafe` | Database name |
| `DSV_DB_USER` | app, init-db, analytics | `dinesafe` | Database user |
| `DSV_DB_PASSWORD` | app, init-db, analytics | `dinesafe` | Database password |
| `DSV_ANALYTICS_URL` | app | `http://dsv-analytics:3000` | Internal Grafana URL for the proxy |
| `DSV_ANALYTICS_ROOT_URL` | analytics | `http://localhost:5000/analytics/` | Public-facing Grafana root URL |
| `DSV_ANALYTICS_ADMIN_USER` | analytics, init-analytics | — | Grafana admin username |
| `DSV_ANALYTICS_ADMIN_PASSWORD` | analytics, init-analytics | — | Grafana admin password |

## Out of scope

- Authentication, pagination, filtering, search
- Map visualization
- CI/CD
- Production hardening (gunicorn, TLS, etc.)
