# Journal 25 — Data Ingestion Refactor Planning

## 2026-05-07 14:00 — Context exploration

**Goal:** Plan data ingestion refactor so the app has 10 years of historical data + daily refresh from Toronto Open Data.

**Current state discovered:**
- `src/db/init.sql`: creates `inspections` table + `_csv_staging` table, loads `Dinesafe.csv` via COPY, transforms into `inspections`, drops staging
- `docker-compose.yml`: mounts `src/db/Dinesafe.csv` to `/data/Dinesafe.csv`, `init.sql` into `docker-entrypoint-initdb.d/`
- Current `Dinesafe.csv` spans 2023-11-10 to 2026-04-27 (~19,400 rows)
- Historical CSVs in `src/db/2023-04-11 - Dinesafe Historical data/` cover 2001–2022 (22 files)
- Historical schema differs from current: 16 cols, double-quoted, has `Rec #`/`Establishment Status`/`Min. Inspections Per Year`, lacks `Inspection Observation`/`Outcome Date`/`unique_id`/`_id`
- `app.py` hardcodes `DATA_START = date(2023, 11, 9)` and `get_valid_years()` returns `range(2023, ...)`
- No existing cron or refresh mechanism — data is static from initial Docker build

**Data sources (user-provided):**
- Recent CSV: `https://ckan0.cf.opendata.inter.prod-toronto.ca/.../Dinesafe.csv`
- Historical ZIP: `https://ckan0.cf.opendata.inter.prod-toronto.ca/.../Dinesafe%20Historical%20Data.zip`
- CKAN API available for metadata/resource discovery

**Key schema differences (from docs/ref/data.md):**
- Historical has `Establishment Status`, `Min. Inspections Per Year` (not in current)
- Current has `Inspection Observation`, `Outcome Date` (not in historical)
- Lat/Lon at different column positions
- Historical all double-quoted

## 2026-05-07 14:30 — Design decisions (brainstorming)

User decisions via Q&A:
- Load ALL historical data (2001–2022), not just 10 years
- Add `establishment_status` and `min_inspections_per_year` to inspections table (NULL for recent rows)
- Daily refresh = full replace of recent data (delete rows >= 2023-11-01, re-insert from fresh CSV)
- Python script (`src/db/refresh.py`) for both seed and refresh
- `init.sql` becomes schema-only; `refresh.py` handles all data loading
- All config values centralized as constants for future config file extraction

Spec written to `docs/superpowers/specs/2026-05-07-data-ingestion-design.md`

## 2026-05-07 15:00 — Implementation plan

Wrote 8-task implementation plan to `docs/superpowers/plans/2026-05-07-data-ingestion.md`.

Tasks: init.sql schema → refresh.py pure functions + tests → DB utilities → seed path → refresh path + main → app.py updates + test fixes → docker-compose cleanup → docs update.

Tests affected by app.py changes:
- `test_q4_2023_clips_to_data_start`: start changes from 2023-11-09 to 2023-10-01
- `test_valid_years_includes_2023_and_current`: rename + assert 2001 in years
