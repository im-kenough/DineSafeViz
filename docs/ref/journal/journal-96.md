# Journal 96

## 2026-07-24 — Local deploy instructions + fix data display for new CSV schema

**Task:** (1) Write instructions to deploy the webapp locally with Docker Desktop
for testing. (2) Fix the webapp so it displays the offline data in
`docs/ref/local-data/` correctly, given the DineSafe CSV columns may have changed.

### Reconnaissance

Ingestion path: `src/dsv-db/refresh.py`. It downloads data **live** from the
Toronto Open Data portal (`urlretrieve` of RECENT_CSV_URL + HISTORICAL_ZIP_URL).
Neither `docs/ref/local-data/` nor `src/data/` is referenced by any code path —
confirmed via grep. `src/data/*.csv` are stale sample copies (old schema).

`csv.DictReader` is header-name-based, so column **reordering** does not break
ingestion; only renamed/removed/added columns matter.

#### Recent CSV header drift (old → new)

OLD (what RECENT_COLUMN_MAP + tests expect):
`_id,unique_id,estId,estName,address,inspectionStatus,inspectionDate,typeDesc,deficiencyDesc,actionDesc,OutcomeDate,OutcomeDesc,amountFined,latitude,longitude`

NEW (`docs/ref/local-data/Dinesafe.csv`, 107,171 data rows):
`_id,unique_id,estId,oldEstId,estName,address,inspectionStatus,phone,inspectionDate,observation,typeDesc,deficiencyDesc,severity,OutcomeDate,OutcomeDesc,amountFined,latitude,longitude`

- **Added:** `oldEstId`, `phone`, `observation`, `severity`
- **Removed:** `actionDesc`
- Reordered (harmless for DictReader).

Impact on current RECENT_COLUMN_MAP:
- `actionDesc → action` now maps to a missing column → `action` is NULL for all
  recent rows. New CSV has NO enforcement/action column at all. Grafana has 3
  panels keyed on `action` (remediation, closed/conditional by action type).
- `severity` is now present in recent data but unmapped (DB has a `severity`
  column; historical rows populate it, recent rows currently do not).
- `observation` is new; `deficiencyDesc` currently maps to `inspection_observation`.
  In new data `observation` = generic sentence ("One or more minor infractions…"),
  `deficiencyDesc` = category ("05. MAINTENANCE / SANITATION…"), `typeDesc` =
  specific infraction ("FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED…"). Semantic
  mapping decision needed.

Historical CSV header unchanged (new copy is just unquoted; DictReader-equivalent).

DB schema `inspections` (init.sql) and displays:
- Webapp `/inspections` table shows: status, infraction_details, establishment
  (name+address), establishment_type, action, outcome, outcome_date, amount_fined.
- Grafana dashboard uses: establishment_status, action, establishment_type,
  infraction_details, inspection_observation, inspection_date.

### Open design decisions (to confirm with user before coding)

A. Local-test data source: wire the offline copy into `refresh.py` (reproducible,
   offline) vs. keep live download. User downloaded offline data "for testing" →
   leaning offline via an env-var-selectable local path.
B. `inspection_observation` mapping: `observation` (generic) vs `deficiencyDesc`
   (category) in the new schema.

### Decisions (confirmed with user)

- A → offline via env toggle `DSV_LOCAL_DATA_DIR` (unset = live download, default).
- B → keep `deficiencyDesc → inspection_observation`.
- Recent map: removed dead `actionDesc→action` (column gone upstream; recent
  `action` now NULL), added `severity→severity` (new in recent feed).

### Implementation

- `refresh.py`: added `DSV_LOCAL_DATA_DIR`; pure helpers `recent_source` /
  `historical_source`; unified reader `_read_csv_rows` used by recent + historical.
- `docker-compose.yml`: `dsv-init-db` gets `DSV_LOCAL_DATA_DIR:-` env + mount
  `./docs/ref/local-data:/data:ro`.
- Tests updated to new recent schema + source-selection + encoding.

### Bugs found by real `docker compose` run (isolated project `dsv-localtest`)

1. **Mixed CSV encodings.** Seed died on `dinesafe_hist_2023.csv`:
   `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc9`. Older historical
   files are UTF-8; the 2023 file is Windows-1252. Fix: `_read_csv_rows` decodes
   UTF-8 first, falls back to cp1252. Verified accented names (`Chérie`, `Café`)
   decode cleanly (no mojibake).
2. **`dsv-app` image did not build (pre-existing, dependabot).** (a) otel version
   conflict — `instrumentation 0.64b0` requires `semantic-conventions 0.64b0` but
   pinned `0.63b1` (and `-psycopg2`/`-wsgi` at 0.63b1); (b) Dockerfile COPYs
   `python3.12` site-packages on a `python3.14` base. Fix (user-approved): pinned
   otel to a consistent `1.43.0 / 0.64b0` set (dry-run-verified in a clean
   python:3.14 container) and corrected Dockerfile paths to `python3.14`.

### `.env.example` gotcha (surfaced, not silently fixed)

`init.sql` hardcodes `GRANT ... ON DATABASE dinesafe`, but `.env.example` ships
`DSV_DB_NAME=dsv-ds`. Any name other than `dinesafe` makes the DB init script
error. Local-testing doc specifies `DSV_DB_NAME=dinesafe`.

### End-to-end verification (isolated stack, offline data)

- Seed: 23 historical files + recent = **502,795 rows**, 2001-01-03 → 2026-07-22,
  "Seed complete."
- DB spot checks: recent rows have `severity` set, `action` NULL (by design);
  status counts Pass 483,837 / Conditional 18,482 / Closed 476.
- Webapp: `dsv-app` healthy; `/inspections?year=2026&q=3` rendered **2,852 rows**
  (status-pass 2400 / conditional 440 / closed 12), status sort correct.
- `pytest` in `src/dsv-db`: 27 passed.
- Torn down with `down -v` (isolated project; user's real `.env`/volumes untouched).
