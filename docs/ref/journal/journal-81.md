# Journal 81

## 2026-06-07 — Investigate #135: grafana dashboard doesn't allow unauthenticated users select date ranges

### Context

Issue #135 reports that unauthenticated users cannot select date ranges on the Grafana dashboard. Assigned to v0.3.0 milestone.

### Investigation

**Files examined:**
- `docker-compose.yml` — Grafana container config, env vars, the `dsv-init-analytics` permissions service
- `src/dsv-analytics/provisioning/dashboards/dinesafe.json` — production dashboard JSON
- `src/dsv-analytics/provisioning/dashboards/dashboard.yml` — provisioning config
- `src/dsv-analytics/provisioning/datasources/datasource.yml` — datasource config

**Noted (not the bug, separate):** There is a stale copy of provisioning config at `src/grafana/provisioning/` that uses `${DB_HOST}` without the `DSV_` prefix. The live config mounted in docker-compose is `src/dsv-analytics/provisioning/` — this one uses the correct `${DSV_DB_HOST}` etc.

**Dashboard JSON analysis:**
- `"editable": true` — dashboard is editable
- `"timepicker": {"refresh_intervals": ["1d"]}` — timepicker is visible (no `"hidden": true`)
- No `hideControls` flag

The time picker is rendered in the UI but not interactive for anonymous users. This rules out the timepicker being deliberately hidden.

**Root cause:**

`GF_USERS_VIEWERS_CAN_EDIT` is not set in the `dsv-analytics` service environment. In Grafana, this setting defaults to `false`, which prevents Viewer-role users (including anonymous) from interacting with time range controls — even though the time picker control is visible.

This is distinct from RBAC/dashboard permissions (which control which dashboards a Viewer can access). `viewers_can_edit` controls whether Viewers can *interact* (change time ranges, template variables) without the ability to save changes.

Grafana docs confirm: `[users] viewers_can_edit = true` / env var `GF_USERS_VIEWERS_CAN_EDIT=true` allows viewers to edit/inspect dashboard settings in the browser, but not save.

### Fix

Added `GF_USERS_VIEWERS_CAN_EDIT: "true"` to the `dsv-analytics` service environment in `docker-compose.yml`.

**Files changed:**
- `docker-compose.yml` — one line added under `dsv-analytics` env

---

## 2026-06-07 — Fix empty DB on fresh provision (broken Toronto Open Data URL)

### Symptom

After fresh VM provision via `make`, DB was empty. `docker compose logs dsv-init-db` showed:
- Historical data (2001–2022) loaded successfully
- Recent CSV download returned `HTTP Error 404: Not Found`
- Because `seed()` calls `conn.commit()` only after both loads, the rollback wiped all historical data too

### Root cause

Toronto Open Data changed/removed the recent CSV resource ID. Old resource:
`eda39233-4791-464e-98e6-094f51a01916` → 404

### Investigation

Queried the CKAN package API:
`https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=b6b4f3fb-2e2c-47e7-931d-b87d22806948`

New CSV resource: `af0f5b8a-4b73-4a50-8781-65e949792b40` (`dinesafe.csv`)

Note: historical ZIP filename also changed in the API (`dinesafe-historical-data.zip` vs old `Dinesafe%20Historical%20Data.zip`), but old URL still resolves so left unchanged.

Side note (not fixed): `seed()` commits only after both downloads succeed — a failure in the recent step rolls back all historical data, requiring a full re-seed. Worth hardening in future.

### Fix

Updated `RECENT_CSV_URL` in `src/dsv-db/refresh.py` to new resource ID and filename.
