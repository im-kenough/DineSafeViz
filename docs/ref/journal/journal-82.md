# Journal 82 — Diagnosing blank data on deployed webapp

## 2026-06-07 — Investigation: home page shows stats but /inspections is blank

**Symptom:** After redeploying `feat/iac-v0.3.0-deploy` to `yyz-app-dsv01`:
- `http://10.0.20.80:5000/` shows correct DB counters (years of data, total inspections)
- `http://10.0.20.80:5000/inspections?year=2026&q=2` shows blank/no data
- `http://10.0.20.80:5000/dashboard` shows blank

**Docker state:** `docker ps` shows dsv-app, dsv-analytics, dsv-db running. The
`dsv-init-db` one-shot container already ran and exited (expected, restart: "no").
User got `getwd: no such file or directory` when trying `docker compose logs` — 
likely current working directory was removed or stale.

**Analysis of data flow:**
1. `init.sql` creates empty `inspections` table (DATE column for inspection_date)
2. `refresh.py` seed() loads historical (2001-2022) then recent (Q4 2023+) and commits once
3. Home page runs `SELECT COUNT(*), MIN(inspection_date), MAX(inspection_date)` — this works
4. `/inspections` runs `SELECT ... WHERE inspection_date BETWEEN %s AND %s` for selected quarter
5. Default view = current year (2026) + current quarter (Q2 = April–June)

**Hypothesis:** Data loaded successfully (home stats confirm this), but the
recent CSV from Toronto Open Data may not include Q2 2026 data yet. The default
view (`/inspections` with no params or `?year=2026&q=2`) shows empty results
because no rows have `inspection_date` between 2026-04-01 and 2026-06-07.

**Diagnostic results from VM:**
- `docker logs dsv-dsv-init-db-1`: Seed completed successfully, historical (22 files)
  + recent (107,164 rows) loaded and committed.
- `SELECT MIN, MAX, COUNT`: min=2001-01-03, max=2022-12-30, count=464,954
  — recent 107K rows all have NULL inspection_date!
- Year distribution: 107,164 rows with NULL year (recent data), rest is 2001-2022.

**Root cause confirmed:** Toronto Open Data changed all CSV column headers.
Old headers like `"Inspection Date"` are now `"inspectionDate"`, `"Establishment Name"`
→ `"estName"`, etc. `map_row()` uses `row.get(old_header)` which silently returns
`None` for every field. All 107K recent rows loaded with all-NULL columns.

**Fix applied:** Updated `RECENT_COLUMN_MAP` in `src/dsv-db/refresh.py` to use the
new CSV headers. Also noted: `Severity` and `Establishment Type` columns were removed
from the CSV. `inspectionStatus` (Pass/Conditional Pass/Closed) mapped to `severity`.
`typeDesc` (violation descriptions) mapped to `infraction_details`.

**Columns removed from new CSV (will be NULL in recent data):**
- `Inspection ID` → no equivalent
- `Establishment Type` → no equivalent
- `Severity` (C-Crucial/S-Significant/M-Minor) → replaced by `inspectionStatus`
  (Pass/Conditional Pass/Closed) — different semantics

**Full fix applied across all layers:**

1. `src/dsv-db/refresh.py` — Updated `RECENT_COLUMN_MAP` to new CSV headers.
   `inspectionStatus` → `establishment_status` (consistent with historical
   `Establishment Status` mapping).

2. `src/dsv-app/app.py` — Replaced `severity` with `establishment_status` in
   SQL query, row mapping, sort logic. `SEVERITY_ORDER` → `STATUS_ORDER`
   (Closed=0, Conditional Pass=1, Pass=2).

3. `src/dsv-app/templates/index.html` — Column header "Severity" → "Status".
   CSS classes `sev-*` → `status-*`. Row references use `establishment_status`.

4. `src/dsv-app/static/style.css` — CSS variables and row classes updated:
   `status-closed` (red), `status-conditional` (orange), `status-pass` (green).

5. Tests updated: `test_helpers.py`, `test_routes.py`, `test_refresh.py` all
   updated to use new column names and values.

**Test results:** 18/18 DB tests pass, 53/54 webapp tests pass (1 pre-existing
version mismatch failure unrelated to this change).

**Remaining: Grafana dashboards** use `severity` column in SQL queries
(src/dsv-analytics/provisioning/dashboards/dinesafe.json). These will need
updating separately to use `establishment_status` with new values.
