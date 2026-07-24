# Local Docker Desktop testing + DineSafe CSV schema fix

**Date:** 2026-07-24
**Status:** Approved

## Problem

1. There is no supported way to run the stack locally against a fixed dataset —
   `refresh.py` only downloads live data from Toronto's Open Data portal, so
   local testing depends on the internet and is not reproducible.
2. The recent DineSafe CSV schema drifted. The offline copy in
   `docs/ref/local-data/Dinesafe.csv` has new/removed columns that the ingestion
   column map no longer matches, so some fields display blank/incorrectly.

## Schema drift (recent CSV)

OLD: `_id,unique_id,estId,estName,address,inspectionStatus,inspectionDate,typeDesc,deficiencyDesc,actionDesc,OutcomeDate,OutcomeDesc,amountFined,latitude,longitude`

NEW: `_id,unique_id,estId,oldEstId,estName,address,inspectionStatus,phone,inspectionDate,observation,typeDesc,deficiencyDesc,severity,OutcomeDate,OutcomeDesc,amountFined,latitude,longitude`

- Added: `oldEstId`, `phone`, `observation`, `severity`
- Removed: `actionDesc`
- Reordered (harmless — `csv.DictReader` is header-name-based).

Historical CSV schema unchanged.

## Design

### 1. `refresh.py` — column map fix (`RECENT_COLUMN_MAP`)
- Remove `"actionDesc": "action"` — column no longer exists upstream; recent
  `action` is now always NULL (no enforcement column in the new feed).
- Add `"severity": "severity"` — new recent data carries severity; DB column
  already exists and historical rows populate it.
- Keep `"deficiencyDesc": "inspection_observation"`.
- `oldEstId`, `phone`, `observation` are discarded (like `_id`).

### 2. `refresh.py` — local data source toggle
- New env var `DSV_LOCAL_DATA_DIR`.
  - Unset (default): current live-download behavior, unchanged.
  - Set: read recent from `{dir}/Dinesafe.csv`; read historical from
    `{dir}/dinesafe-historical/*.csv`. No network access.
- Implemented behind two small helpers so the branch lives in one place.

### 2b. `refresh.py` — mixed-encoding CSV reader (found during verification)
- Historical files mix encodings (older years UTF-8, newer files Windows-1252);
  the offline `dinesafe_hist_2023.csv` crashed the UTF-8-only reader.
- Unified reader `_read_csv_rows(path, column_map)` decodes UTF-8 first and falls
  back to cp1252. Used by both the recent and historical load paths.

### 2c. `dsv-app` build fix (pre-existing, user-approved — blocks local run)
- `requirements.txt`: align OpenTelemetry to a consistent `1.43.0 / 0.64b0` set
  (was mixing `1.42.1` + `0.63b1`/`0.64b0`, an unsatisfiable pin).
- `Dockerfile`: multi-stage `COPY` referenced `python3.12` site-packages on a
  `python3.14` base; corrected to `python3.14`.

### 3. `docker-compose.yml`
- `dsv-init-db`: add `DSV_LOCAL_DATA_DIR: ${DSV_LOCAL_DATA_DIR:-}` and mount
  `./docs/ref/local-data:/data:ro`. Toggle off ⇒ mount unused, prod behavior
  unchanged.

### 4. Instructions — `docs/how-to/7-run-locally.md`
- Docker Desktop local run: prerequisites, `.env` setup incl.
  `DSV_LOCAL_DATA_DIR=/data`, `docker compose up --build`, URLs
  (`:8080` app, `/analytics/` Grafana), reset with `down -v`, data provenance.

### 5. Tests — `src/dsv-db/tests/test_refresh.py`
- Update recent sample row to new schema; assert `severity` maps through and
  `action` is None.
- Add a test for the source-selection helper (local dir vs live URL).

## Verification
- `pytest` in `src/dsv-db` passes.
- `docker compose up --build` with toggle on seeds cleanly; webapp at
  `http://localhost:8080/inspections` renders inspection rows (recent `action`
  shows "—" as expected). Screenshot captured.

## Out of scope
- `action` cannot be restored for recent data (removed upstream).
- No changes to the Flask app queries or Grafana dashboard.
- `.env.example` shipped `DSV_DB_NAME=dsv-ds`, but `init.sql` hardcodes database
  `dinesafe`. Corrected the example to `dinesafe` and added the
  `DSV_LOCAL_DATA_DIR` toggle entry (user-approved follow-up).
