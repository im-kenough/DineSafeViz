# Data ingestion refactor

## Summary

Replace the static CSV-mount approach with a Python script
(`src/db/refresh.py`) that handles both initial seeding (historical +
recent data) and daily refresh of the `inspections` table.
`init.sql` becomes schema-only. A cron job calls `refresh.py` daily
to keep the dataset current.

## Goals

- Load all historical data (2001–2022) and recent data (2023–present)
  into a single `inspections` table
- Fetch new data daily from Toronto Open Data with no manual
  intervention
- Keep the DB in a consistent state at all times (transactional
  updates)
- Centralize all configurable values (URLs, dates, DB params) for
  future extraction into a config file

## Schema

The `inspections` table gains two columns from the historical dataset.
`init.sql` creates this schema and nothing else (no staging table, no
COPY, no data loading).

```sql
CREATE TABLE inspections (
    id                          SERIAL PRIMARY KEY,
    establishment_id            TEXT,
    inspection_id               TEXT,
    establishment_name          TEXT,
    establishment_type          TEXT,
    establishment_address       TEXT,
    infraction_details          TEXT,
    inspection_observation      TEXT,
    inspection_date             DATE,
    severity                    TEXT,
    action                      TEXT,
    outcome                     TEXT,
    outcome_date                TEXT,
    amount_fined                TEXT,
    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
    unique_id                   TEXT,
    establishment_status        TEXT,
    min_inspections_per_year    TEXT
);
```

Columns that exist only in historical data (`establishment_status`,
`min_inspections_per_year`) are NULL for recent rows. Columns that
exist only in recent data (`inspection_observation`, `outcome_date`,
`unique_id`) are NULL for historical rows.

## `refresh.py`

**Location:** `src/db/refresh.py`

### Configuration block

All configurable values live in constants at the top of the file:

- `CKAN_BASE_URL` — Toronto Open Data base URL
- `RECENT_CSV_URL` — direct download URL for the recent dataset
- `HISTORICAL_ZIP_URL` — direct download URL for the historical ZIP
- `RECENT_DATA_START_DATE` — boundary date (`2023-11-01`); rows at
  or after this date belong to the "recent" partition
- `HISTORICAL_FILE_PATTERN` — filename pattern for CSVs inside the
  ZIP (`dinesafe_hist_{year}.csv`)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — read
  from environment variables with sensible defaults

### Detection logic

```
count = SELECT COUNT(*) FROM inspections
if count == 0 → seed()
else           → refresh()
```

### Seed path (`seed()`)

Runs on first deploy when the table is empty.

1. **Download historical ZIP** from `HISTORICAL_ZIP_URL` to a temp
   directory
2. **Extract and load each CSV** — for each `dinesafe_hist_YYYY.csv`:
   - Read with `csv.DictReader`
   - Map the 16-column historical schema to the unified schema:

     | Historical column            | inspections column           |
     |------------------------------|------------------------------|
     | Rec #                        | (discard)                    |
     | Establishment ID             | establishment_id             |
     | Inspection ID                | inspection_id                |
     | Establishment Name           | establishment_name           |
     | Establishment Type           | establishment_type           |
     | Establishment Address        | establishment_address        |
     | Latitude                     | latitude                     |
     | Longitude                    | longitude                    |
     | Establishment Status         | establishment_status         |
     | Min. Inspections Per Year    | min_inspections_per_year     |
     | Infraction Details           | infraction_details           |
     | Inspection Date              | inspection_date              |
     | Severity                     | severity                     |
     | Action                       | action                       |
     | Outcome                      | outcome                      |
     | Amount Fined                 | amount_fined                 |
     | (not in historical)          | inspection_observation=NULL  |
     | (not in historical)          | outcome_date=NULL            |
     | (not in historical)          | unique_id=NULL               |

   - Bulk insert via `psycopg2` (using `copy_from` with a `StringIO`
     buffer for speed)
3. **Download and load recent CSV** from `RECENT_CSV_URL`:
   - Read with `csv.DictReader`
   - 1:1 column mapping; `_id` discarded (same as `Rec #` in
     historical), `establishment_status` and
     `min_inspections_per_year` set to NULL
   - Bulk insert same as above

### Refresh path (`refresh()`)

Runs daily via cron when the table already has data.

1. Download `Dinesafe.csv` from `RECENT_CSV_URL` to a temp file
2. Parse with `csv.DictReader`
3. In a single transaction:
   - `DELETE FROM inspections WHERE inspection_date >= RECENT_DATA_START_DATE`
   - Bulk insert all rows from the downloaded CSV
   - `COMMIT`

Historical data (pre-2023) is never touched after the initial seed.
The transaction ensures the table is never in a partial state — if
the download or insert fails, old data remains intact.

## App changes

### `src/web/app.py`

- `DATA_START` changes from `date(2023, 11, 9)` to `date(2001, 1, 1)`
- `get_valid_years()` returns `range(2001, date.today().year + 1)`

### `docker-compose.yml`

- Remove the `./src/db/Dinesafe.csv:/data/Dinesafe.csv` volume mount
- `init.sql` mount stays (schema-only)

## Cron integration

The user adds a cron entry on the host:

```
0 6 * * * cd /path/to/DineSafeViz && python3 src/db/refresh.py
```

`refresh.py` needs network access to the Postgres container. Two
options to document:

1. Run on the Docker host with `DB_HOST=localhost` and a published
   Postgres port
2. Run via `docker compose exec db python3 /path/to/refresh.py`
   (requires Python in the Postgres container or a dedicated
   container)

## Files touched

| File                    | Change                                        |
|-------------------------|-----------------------------------------------|
| `src/db/init.sql`       | Add 2 columns, remove staging/COPY/INSERT     |
| `src/db/refresh.py`     | New file — seed + refresh logic               |
| `src/web/app.py`        | Update `DATA_START`, `get_valid_years()`       |
| `docker-compose.yml`    | Remove CSV volume mount                        |
| `docs/ref/data.md`      | Document unified schema with new columns       |
