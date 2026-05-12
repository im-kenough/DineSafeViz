# Application architecture

This document describes the application architecture of DineSafeViz:
the Docker Compose services, the Flask web app, the analytics
dashboard, and how they fit together. For data-layer details see
[data architecture](arch-data.md). For infrastructure and deployment
see [IaC architecture](arch-iac.md).

DineSafeViz runs as a Docker Compose stack on a single VM. The stack
contains five primary services (three long-running, two one-shot) plus
two legacy services that are slated for removal.

![Architecture overview](../img/root-readme/arch-over.drawio.png)

## Services

The primary services and their relationships are described below.

### Long-running services

- **`dsv-db`** — `postgres:17.9`. Stores all DineSafe inspection data
  in a single `inspections` table. Data persists in a named volume
  (`dsv-db-data`). Exposes a `pg_isready` healthcheck that dependent
  services gate their startup on.

- **`dsv-app`** — `python:3.14-slim`. Runs the Flask web app on port
  5000. Connects to `dsv-db` for inspection queries and reverse-proxies
  the Grafana dashboard at `/analytics/`. Starts after `dsv-db` is
  healthy and `dsv-analytics` has started.

- **`dsv-analytics`** — `grafana/grafana:11.6.0`. Serves a
  pre-provisioned Grafana dashboard on port 3000. Uses `dsv-db` as its
  PostgreSQL data source. Accessible directly at
  `localhost:3000/analytics/` or through the Flask proxy at
  `localhost:5000/analytics/`. Dashboard state persists in a named
  volume (`dsv-analytics-data`). Anonymous viewer access is enabled so
  the embedded dashboard works without login.

### One-shot services

- **`dsv-init-db`** — `python:3.14-slim`. Runs `refresh.py` on
  startup. Seeds the database on first run; refreshes recent data on
  subsequent runs. Exits after completion (`restart: "no"`). See
  [data architecture — data ingestion](arch-data.md#data-ingestion)
  for details.

- **`dsv-init-analytics`** — `curlimages/curl:latest`. Waits for
  Grafana to become healthy, then grants Viewer-role access to the
  provisioned dashboard via the Grafana API. Required because Grafana
  11 RBAC doesn't grant anonymous viewers dashboard access by default.

### Legacy services

The compose file also contains `grafana` and `init-grafana` services.
These are the predecessors to `dsv-analytics` and `dsv-init-analytics`
and reference an undefined `db` service and old-style environment
variables (`DB_*`, `GF_*`). They don't function in the current stack
and are candidates for removal.

## Web app

The Flask app at `src/dsv-app/app.py` serves four pages and one proxy
endpoint.

| Route | Description |
|---|---|
| `GET /` | Home page with summary statistics (total inspections, years of data) |
| `GET /inspections` | Inspection log, filterable by year and quarter |
| `GET /dashboard` | Embeds the Grafana dashboard via iframe |
| `GET /info` | Background on the DineSafe dataset |
| `/analytics/<path>` | Reverse proxy to the internal Grafana container (all HTTP methods) |

### Inspection browsing

Inspections are grouped by date and sorted by severity within each
day (Crucial > Significant > Minor > NA > None). Year and quarter
navigation covers 2001 to the present. The navigation uses a dropdown
with flyout menus — recent years are shown directly, older years are
nested under an "Archive" section.

### Home page caching

The home page queries aggregate stats (total inspections and years of
data) from the database and caches the result in memory with a 5-day
TTL to avoid repeated queries on a dataset that changes infrequently.

### Analytics proxy

The `/analytics/` route reverse-proxies all requests to the internal
`dsv-analytics` container using a persistent `requests.Session`.
Hop-by-hop headers (`content-encoding`, `content-length`,
`transfer-encoding`, `connection`) are stripped from the proxied
response. The proxy supports GET, POST, PUT, PATCH, DELETE, and
OPTIONS methods.

## Analytics dashboard

The Grafana dashboard ("DineSafe Inspections Metrics") reads directly
from the PostgreSQL database and renders visualizations. It's
provisioned from files at startup — no manual Grafana UI setup is
needed.

Dashboard panels are organized into sections:

- **Inspection overview:** total inspections, pass/conditional
  pass/closed counts and percentages
- **Trends:** inspections over time, inspections by day of week
- **Enforcement:** enforcement and remediation breakdowns
- **Severity breakdown:** dedicated sections for crucial, significant,
  and minor infractions, each with panels for breakdowns by
  establishment type, enforcement action type, infraction details,
  and inspection observations

## Data model

One table: `inspections` (19 columns). See
[data architecture](arch-data.md) for the full schema, data sources,
and ingestion logic.

## File layout

```text
DineSafeViz/
├── docker-compose.yml
└── src/
    ├── dsv-db/
    │   ├── Dockerfile
    │   ├── init.sql              (creates table schema on first start)
    │   ├── refresh.py            (data seeding and daily refresh)
    │   ├── requirements.txt
    │   └── tests/
    │       └── test_refresh.py
    ├── dsv-analytics/
    │   └── provisioning/
    │       ├── dashboards/       (dashboard.yml, dinesafe.json)
    │       └── datasources/      (datasource.yml)
    ├── dsv-app/
    │   ├── Dockerfile
    │   ├── app.py
    │   ├── requirements.txt
    │   ├── requirements-dev.txt
    │   ├── VERSION.txt
    │   ├── static/
    │   │   ├── style.css
    │   │   ├── favicon/
    │   │   └── fonts/            (IBM Plex Sans .woff2)
    │   ├── templates/
    │   │   ├── base.html
    │   │   ├── home.html
    │   │   ├── index.html
    │   │   ├── dashboard.html
    │   │   └── info.html
    │   └── tests/
    │       ├── conftest.py
    │       ├── test_helpers.py
    │       ├── test_home.py
    │       ├── test_routes.py
    │       ├── test_proxy.py
    │       └── test_dashboard.py
    └── grafana/                  (legacy — duplicate of dsv-analytics)
        └── provisioning/
            ├── dashboards/
            └── datasources/
```

## Configuration

All services are configured via environment variables, typically set
in a `.env` file on the deployment target. The `.env` is templated
from Ansible Vault at deploy time — see
[security architecture](arch-security.md) for secrets management.

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

## Related documents

- [Data architecture](arch-data.md) — data sources, schema, ingestion,
  and refresh logic
- [IaC architecture](arch-iac.md) — image pipeline, VM provisioning,
  and app deployment
- [Security architecture](arch-security.md) — secrets management, VM
  hardening, container security
- [Testing architecture](arch-testing.md) — unit tests, functional
  tests, and gaps
- [CI/CD architecture](arch-ci-cd.md) — release automation and
  dependency management
- [Monitoring architecture](arch-monitoring.md) — planned observability
  stack
