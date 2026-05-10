# Journal 34 — Fix GitHub Issue #60: Missing Q1-Q3 2023 Data

## 2026-05-07 00:00

**Task**: Fix missing Q1-Q3 2023 data in DB import (issue #60).

**Hypothesis**: A hard-coded date in the import logic creates a gap between the historical CSV's end date and the current CSV's start date.

**Investigation**: Downloaded both data sources to check actual date ranges.
- Historical ZIP: 2001-01-03 through 2022-12-30 (22 yearly CSVs)
- Recent CSV: 2023-11-10 through 2026-05-06
- Gap: Jan 2023 – Nov 9 2023 (upstream data gap — neither source covers it)
- `RECENT_DATA_START_DATE = "2023-11-01"` was hard-coded at `refresh.py:34`

**Root cause**: The hard-coded `RECENT_DATA_START_DATE` is fragile — if the upstream recent CSV changes its window, the cutoff won't track. More importantly, the constant's existence obscures that there IS a gap in upstream data. The real issue is that the refresh `DELETE` should use the actual min date from the fresh CSV.

**Fix applied**:
- Removed hard-coded `RECENT_DATA_START_DATE` constant
- Added `min_inspection_date(rows)` helper that computes earliest date from downloaded rows
- `refresh()` now uses computed cutoff from the actual CSV data
- Added 2 tests for `min_inspection_date`

**Files edited**:
- `src/dsv-db/refresh.py` — removed constant, added helper, updated refresh()
- `src/dsv-db/tests/test_refresh.py` — added TestMinInspectionDate class

**Verification**: All 18 db tests + 47 web tests pass.

**Note**: The Q1-Q3 2023 gap is an upstream Toronto Open Data issue — the data simply doesn't exist in either source. This fix prevents future gaps caused by the hard-coded date not tracking the actual data window.
