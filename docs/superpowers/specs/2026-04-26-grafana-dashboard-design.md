# Grafana Dashboard Design Spec

## Overview

Add a Grafana dashboard to DineSafeViz that visualizes DineSafe inspection data
through 11 panels (3 stat cards + 8 charts). Grafana runs inside the existing
Docker Compose stack with no exposed ports. Flask proxies all Grafana requests
and serves a `/dashboard` page with a full-page iframe. The dashboard and all
Grafana config are provisioned as code.

## Architecture

```
Browser
  |
  |-- GET /              --> Flask (index.html, existing inspection table)
  |-- GET /dashboard     --> Flask (dashboard.html with iframe)
  |-- GET /grafana/...   --> Flask proxy --> Grafana (internal, port 3000)
```

- Grafana has **no published ports** in docker-compose. It is only reachable
  from Flask over the internal Docker network.
- Grafana is configured for **anonymous read-only access** (Viewer role). Login
  form is disabled. No editing, no admin access.
- The iframe uses Grafana's `?kiosk` parameter to hide Grafana's native
  nav/header.

## Docker Compose Changes

New service added to `docker-compose.yml`:

```yaml
grafana:
  image: grafana/grafana:11.6.0
  environment:
    GF_SERVER_ROOT_URL: /grafana/
    GF_SERVER_SERVE_FROM_SUB_PATH: "true"
    GF_AUTH_ANONYMOUS_ENABLED: "true"
    GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
    GF_AUTH_DISABLE_LOGIN_FORM: "true"
    GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /etc/grafana/provisioning/dashboards/dinesafe.json
    DB_HOST: db
    DB_PORT: 5432
    DB_NAME: ${DB_NAME}
    DB_USER: ${DB_USER}
    DB_PASSWORD: ${DB_PASSWORD}
  volumes:
    - ./src/grafana/provisioning:/etc/grafana/provisioning
  depends_on:
    db:
      condition: service_healthy
```

No published ports. Depends on `db` health check.

## Grafana Provisioning (Dashboard as Code)

All files under `src/grafana/provisioning/`:

```
src/grafana/provisioning/
  datasources/
    datasource.yml          # PostgreSQL datasource using env vars
  dashboards/
    dashboard.yml           # File-based dashboard provider config
    dinesafe.json           # Dashboard JSON (11 panels)
```

### Datasource (`datasource.yml`)

PostgreSQL datasource pointing to `$DB_HOST:$DB_PORT/$DB_NAME` with
`$DB_USER`/`$DB_PASSWORD`. Uses Grafana's env var interpolation so
credentials are not hardcoded.

### Dashboard provider (`dashboard.yml`)

Points Grafana at the `/etc/grafana/provisioning/dashboards/` directory
to auto-load `dinesafe.json` on startup.

### Dashboard panels (`dinesafe.json`)

UID: `dinesafe`. Title: "DineSafe Inspections".

**Row 1 — Overview stats (stat panels):**

| Panel | Query |
|-------|-------|
| Total Inspections | `COUNT(*)` from inspections |
| Crucial Infractions | `COUNT(*)` WHERE severity = 'C - Crucial' |
| Total Fines Collected | `SUM(amount_fined::numeric)` WHERE amount_fined IS NOT NULL |

**Row 2 — Time series (full width):**

| Panel | Type | Query |
|-------|------|-------|
| Inspections Over Time | Line chart | `COUNT(*)` grouped by `date_trunc('week', inspection_date)` |
| Fines Issued Over Time | Bar chart | `SUM(amount_fined::numeric)` grouped by `date_trunc('month', inspection_date)` |

**Row 3 — Breakdowns:**

| Panel | Type | Query |
|-------|------|-------|
| Severity Breakdown | Pie chart | `COUNT(*)` grouped by severity |
| Outcome Distribution | Pie chart | `COUNT(*)` grouped by outcome, excluding NULLs/None |

**Row 4 — Rankings & patterns:**

| Panel | Type | Query |
|-------|------|-------|
| Top 10 Most-Inspected Establishments | Horizontal bar | `COUNT(*)` grouped by establishment_name, LIMIT 10 |
| Actions Taken Over Time | Stacked area | `COUNT(*)` grouped by action + `date_trunc('month', inspection_date)` |

**Row 5 — Deep dives:**

| Panel | Type | Query |
|-------|------|-------|
| Crucial Infractions by Establishment Type | Horizontal bar | `COUNT(*)` WHERE severity = 'C - Crucial' grouped by establishment_type, LIMIT 10 |
| Inspections by Day of Week | Bar chart | `COUNT(*)` grouped by `EXTRACT(dow FROM inspection_date)`, labels Mon-Sun |

## Flask Changes

### New dependency

Add `requests` to `requirements.txt`.

### New route: `/dashboard`

Renders `dashboard.html` — a minimal template with:
- A nav link back to the home page
- A full-page iframe pointing to `/grafana/d/dinesafe/dinesafe-inspections?kiosk`

### New route: `/grafana/<path:path>` (catch-all proxy)

Uses the `requests` library to forward requests to `http://grafana:3000/grafana/<path>`:
- Forwards method, headers, and body
- Returns Grafana's response (status, headers, body)
- Streams responses to avoid buffering large assets

### Home page change

Add a "Dashboard" nav link to `index.html` header area, styled consistently
with existing year/quarter tabs, pointing to `/dashboard`.

## File Changes Summary

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `grafana` service |
| `src/grafana/provisioning/datasources/datasource.yml` | New file |
| `src/grafana/provisioning/dashboards/dashboard.yml` | New file |
| `src/grafana/provisioning/dashboards/dinesafe.json` | New file |
| `src/web/app.py` | Add `/dashboard` route and `/grafana/<path>` proxy |
| `src/web/templates/dashboard.html` | New template with iframe |
| `src/web/templates/index.html` | Add "Dashboard" nav link |
| `src/web/requirements.txt` | Add `requests` |
