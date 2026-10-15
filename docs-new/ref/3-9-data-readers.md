# Data readers

This page describes how `dsv-app` and `dsv-analytics` read the `inspections`
table. For the overview, see [Data architecture](3-1-data-architecture.md).

## Readers

Two services read Postgres, both as `dinesafe_app`: `SELECT` only, with a
10-second `statement_timeout`. Neither writes.

| Reader          | Code                              | Connection                                                       | Caching                                              |
| --------------- | --------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------- |
| `dsv-app`       | `src/dsv-app/app.py`              | New psycopg2 connection per query. No pool. 5 s connect timeout. | Inspection count and date range, in memory, 5-day TTL |
| `dsv-analytics` | `src/dsv-analytics/provisioning/` | Provisioned data source `dinesafe-postgres`, `sslmode: disable`  | None. Panels query on every dashboard load.          |

- `load_log` is readable, but nothing displays it yet.
- Connections are plaintext, on the internal `backend` network only.

### Grain: one row per infraction

Both readers depend on how `inspections` stores an inspection.

| `establishment_id`   | `inspection_date` | `establishment_status` | `severity`  | `infraction_details`                              |
| -------------------- | ----------------- | ---------------------- | ----------- | ------------------------------------------------- |
| `001Vo000013QjdPIAS` | 2026-04-21        | Pass                   | M - Minor   | FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED …      |
| `001Vo000013QjdPIAS` | 2026-04-21        | Pass                   | M - Minor   | FOOD PREMISE NOT MAINTAINED TO KEEP …             |
| `10500438`           | 2017-12-05        | Pass                   | `NULL`      | `NULL`                                            |

- Rows 1 and 2: one inspection with two infractions. Row 3: a clean
  inspection, one row with `NULL` infraction fields.
- An inspection is an `(establishment_id, inspection_date)` pair. Recent rows
  have no `inspection_id`.
- The app and Grafana both count `DISTINCT establishment_id, inspection_date`,
  so their totals match: about 333,000 inspections in about 508,000 rows.



