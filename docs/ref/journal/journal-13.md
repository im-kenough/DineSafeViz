# Journal 13

## 2026-04-27 — Fix Grafana dashboard "Access denied" for anonymous viewers

### Problem
`localhost:5000/dashboard` showed "Failed to load dashboard — Access denied to this dashboard" in the iframe.

### Investigation
- DB has data (min: 2023-11-10, max: 2026-04-10, 634 rows in last 90 days) — not a data/time range issue.
- Grafana datasource health check: OK.
- `curl -s http://localhost:3000/grafana/api/dashboards/uid/dinesafe` → HTTP 403 "Access denied to this dashboard" for anonymous users.
- `GF_AUTH_ANONYMOUS_ENABLED: "true"` and `GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer` are set, but Grafana 11 RBAC requires explicit dashboard-level permissions even for org Viewer role.
- Dashboard permissions were empty (`[]`).

### Root cause
Grafana 11 RBAC: anonymous Viewer org role no longer implicitly grants access to dashboards. Explicit dashboard-level permissions are required. Additionally, there was no persistent `dsv-analytics-data` volume, so any API-set permissions were lost on container restart.

### Fix
1. Added `dsv-analytics-data:/var/lib/grafana` volume to the grafana service in docker-compose.yml — persists Grafana's internal SQLite database across restarts.
2. Added `init-grafana` service that waits for Grafana to be ready, then grants Viewer role access to the dashboard via API. Runs once and exits.

### Files changed
- `docker-compose.yml`
