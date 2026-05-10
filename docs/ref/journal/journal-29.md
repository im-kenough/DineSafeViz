# Journal 29

## 2026-05-07 — /simplify pass on task-db-hx branch

Ran simplify review across all branch changes (refresh.py, app.py, docker-compose.yml, tests).

### Changes made

**src/dsv-db/refresh.py**
- Removed unused `CKAN_BASE_URL` and `HISTORICAL_FILE_PATTERN` constants (defined but never referenced).
- Merged `map_historical_row` and `map_recent_row` into `map_row(row, column_map)` — identical 3-line bodies differing only in which column map they used.
- Extracted `_fetch_recent_rows()` from the duplicated download/parse block that appeared in both `download_and_load_recent` (seed path) and `refresh` (refresh path). Both callers now delegate to `_fetch_recent_rows()`. The download-before-delete invariant in `refresh` is preserved.
- Removed redundant inline comment "Single transaction: delete stale rows..." from `refresh()` (covered by docstring).

**src/dsv-app/app.py**
- Moved `_hop_by_hop` set from inside `grafana_proxy` to module-level constant `_HOP_BY_HOP`. Grafana dashboards trigger many asset requests — no need to reallocate this set on each one.

**docker-compose.yml**
- Fixed `init-grafana` entrypoint: changed `exit 1` to `exit 0` when the dashboard UID isn't found. The log message says "skipping" — a hard exit 1 contradicted this and could mislead Docker into marking the service as failed.

**src/dsv-db/tests/test_refresh.py**
- Updated imports and all call sites from `map_historical_row`/`map_recent_row` to `map_row(row, HISTORICAL_COLUMN_MAP)` and `map_row(row, RECENT_COLUMN_MAP)`.

### Verification
- `src/dsv-db`: 16 passed
- `src/dsv-app`: 44 passed
