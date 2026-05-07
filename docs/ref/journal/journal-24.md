# Journal 24

## 2026-05-05 14:00

**Task:** Examine historical CSV files (2001-2015) in
`src/db/2023-04-11 - Dinesafe Historical data/` and document their
structure in `docs/ref/data.md`.

### Actions

- Listed files: 22 CSV files, `dinesafe_hist_2001.csv` through
  `dinesafe_hist_2022.csv`.
- Read headers from 2001, 2005, 2010, 2015 — all share the same
  16-column schema. No schema drift across years.
- Columns (historical):
  `Rec #, Establishment ID, Inspection ID, Establishment Name,
  Establishment Type, Establishment Address, Latitude, Longitude,
  Establishment Status, Min. Inspections Per Year, Infraction Details,
  Inspection Date, Severity, Action, Outcome, Amount Fined`
- Compared to current dataset columns (from data.md):
  `_id, Establishment ID, Inspection ID, Establishment Name,
  Establishment Type, Establishment Address, Infraction Details,
  Inspection Observation, Inspection Date, Severity, Action, Outcome,
  Outcome Date, Amount Fined, Latitude, Longitude, unique_id`
- Key differences:
  - Historical has `Rec #` (row counter); current has `_id` + `unique_id`.
  - Historical has `Establishment Status` and `Min. Inspections Per Year`;
    current does not.
  - Current has `Inspection Observation` and `Outcome Date`;
    historical does not.
  - Lat/Lon position differs (cols 7-8 in historical, cols 15-16 in current).
- Naive `cut -d','` failed because Infraction Details contains commas.
  Switched to Python csv module.
- Collected all enum values for Status, Severity, Action, Outcome,
  Establishment Type across 2001-2015.
- Checked nullability: ~34-40% of rows have empty infraction/severity/action
  (clean inspections). Outcome and Amount Fined are rare (<2% of rows).
- Row counts grow from ~6k (2001) to ~22k (2015).

### Decision

Document the historical schema as a new section in `docs/ref/data.md`,
highlighting differences from the current schema and import-relevant
observations (column mapping, enum values, nullability patterns).
