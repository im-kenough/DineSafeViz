# Data mapping

This page describes how DineSafeViz loads the DineSafe datasets into
PostgreSQL. It covers the database schema, how historic and recent columns
map to one table, and the gaps that remain. For the upstream datasets and
their data dictionaries, see [Data sources](./data-sources.md).

The source of truth is the code:

- `src/dsv-db/init.sql`: roles, table, and index.
- `src/dsv-db/migrations/001_load_log.sql`: the `load_log` table and the
  loader role's final grants.
- `src/dsv-pipeline/dinesafe_csv.py`: the CSV column maps and encoding helpers.
- `src/dsv-pipeline/loader.py`: the seed and refresh logic and row transforms.
- `src/dsv-pipeline/pipeline.py`: chooses seed, refresh, or skip, and commits.
- `src/dsv-app/app.py` and
  `src/dsv-analytics/provisioning/dashboards/dinesafe.json`: the queries that
  read the table.

## How the database is created

The database is built in two stages. Postgres creates an empty schema, and
then a one-shot container fills it.

1. `dsv-db` (`postgres:18.6`) starts. On the first start only, when the
   `dsv-db-data` volume is empty, Postgres runs `init.sql` and
   `set-passwords.sh` from `/docker-entrypoint-initdb.d/`, in that order.
   With the migrations that `deploy.sh` applies next, they create:
   - the `inspections` table and an index on `inspection_date`.
   - the `load_log` table, which records each load.
   - `dinesafe_app`, a role with `SELECT` on both tables and a 10-second
     `statement_timeout`. `dsv-app` and Grafana use this role.
   - `dinesafe_migrator`, the role the data pipeline loads as, with
     `SELECT`, `INSERT`, and `DELETE` on `inspections` and `load_log`, and
     no `CREATE`, `UPDATE`, `TRUNCATE`, or `DROP`.
   - the passwords for both roles, from `DSV_DB_APP_PASSWORD` and
     `DSV_DB_MIGRATOR_PASSWORD`.
2. `scripts/deploy.sh` runs every file in `src/dsv-db/migrations/` as the
   superuser on every deploy, before the load. It's the only place
   migrations run, so they're idempotent.
3. `dsv-pipeline load` fills the table. It takes a Postgres advisory lock,
   so two loads can't run at once, then picks one action:
   - **Empty table, or a new complete `historical/` folder:** `seed()`
     empties the table, then loads the historical data and the recent data.
   - **Newest raw-zone file not loaded yet, or `--force`:** `refresh()`
     replaces the recent data.
   - **Newest raw-zone file already loaded:** it skips, and changes nothing.

   It downloads only the files it needs from the Blob raw zone, and commits
   the seed or refresh together with a `load_log` row in one transaction.

<!-- prettier-ignore -->
> [!NOTE]
> `init.sql` grants privileges on a database named `dinesafe`. If you set
> `DSV_DB_NAME` to anything else, the grants fail.

On the Azure VMs, `dsv-pipeline.timer` runs `scripts/pipeline.sh <env> run`
each business-day morning. Locally, it runs on `./scripts/deploy.sh dev` or
`./scripts/pipeline.sh dev load`, never on `docker compose up`. See
[Data landing zone](../explanation/data-landing-zone.md#the-etl-logic).

### Seed path

`seed()` runs as a single transaction and commits once at the end:

1. Scan the recent CSV once for the cutoff, the earliest `inspection_date`,
   and the duplicate rows filed under an old ID (see
   [Old ID duplicates](#old-id-duplicates)). With the current feed, the
   cutoff is `2023-11-10`.
2. Delete every row in `inspections`.
3. Load each historical CSV in filename order, streaming its rows (see
   [Row processing](#row-processing)). Rows dated on or after the cutoff are
   skipped. `dinesafe_hist_2023.csv` runs to `2023-12-29`, so its rows from
   the overlap window are dropped in favor of the recent feed.
4. Stream the recent CSV again, drop the old-ID duplicates, and bulk-insert
   the rest.

`seed()` doesn't commit. `pipeline.py` adds the `load_log` row and commits
once.

With the October 14, 2026 download, a seed inserts 508,445 rows: 390,835
historical rows (4,791 rows of `dinesafe_hist_2023.csv` fall in the overlap
and are skipped) and 117,610 recent rows.

### Refresh path

`refresh()` scans the recent CSV for the cutoff and the old-ID duplicates
first. Then it runs `DELETE FROM inspections WHERE inspection_date >= cutoff` and inserts
the new rows. `pipeline.py` adds the `load_log` row and commits all three in
one transaction, so readers never see a partially loaded table. Historical
rows stay in place because they're older than the cutoff.

Because the whole window is replaced, a refresh also picks up rows that TPH
changed or removed, not only new ones.

### Row processing

`_read_csv_rows()` and `map_row()` apply these steps to every row from
either dataset:

- **Encoding:** decode as UTF-8 (BOM-tolerant), and fall back to cp1252
  if any byte in the file isn't valid UTF-8. The recent file and the 2001
  to 2022 historical files are UTF-8; `dinesafe_hist_2023.csv` is cp1252.
- **Column mapping:** rename the CSV columns to the unified schema using
  `HISTORICAL_COLUMN_MAP` or `RECENT_COLUMN_MAP`. Any target column that
  the source doesn't provide is set to `NULL`.
- **Nulls:** turn empty strings and the literal string `"None"` into `NULL`.
- **Dates:** convert `MM/DD/YYYY` (used only in `dinesafe_hist_2023.csv`)
  to ISO `YYYY-MM-DD`.
- **Address split:** split `establishment_address` into `street`, `unit`,
  and `postal_code` (see [Address formats](#address-formats)).
- **Insert:** load with `COPY`. Tabs, carriage returns, and newlines inside
  values become spaces.

Values aren't otherwise cleaned. For example, `typeDesc` values keep their
trailing spaces.

## Schema

All inspection data lives in one denormalized table, `inspections`. Each
row is **one infraction**. An inspection with no infractions is a single row
with `NULL` infraction fields. Nothing in the table identifies an inspection directly,
so the app and the Grafana dashboard both treat an inspection as one
`(establishment_id, inspection_date)` pair and count it with `SELECT
DISTINCT`.

| Column                     | Type             | Notes                                           |
| -------------------------- | ---------------- | ----------------------------------------------- |
| `id`                       | SERIAL PK        | Surrogate key                                   |
| `establishment_id`         | TEXT             | Numeric (historic) or Salesforce-style (recent) |
| `inspection_id`            | TEXT             | Historic only                                   |
| `establishment_name`       | TEXT             |                                                 |
| `establishment_type`       | TEXT             | Historic only                                   |
| `establishment_address`    | TEXT             | Raw address as supplied                         |
| `infraction_details`       | TEXT             | Specific infraction text                        |
| `infraction_category`      | TEXT             | Recent only                                     |
| `inspection_date`          | DATE             | Indexed                                         |
| `severity`                 | TEXT             | `C - Crucial`, `S - Significant`, `M - Minor`, … |
| `action`                   | TEXT             | Historic only                                   |
| `outcome`                  | TEXT             | Court outcome                                   |
| `outcome_date`             | TEXT             | Recent only                                     |
| `amount_fined`             | TEXT             |                                                 |
| `latitude`                 | DOUBLE PRECISION |                                                 |
| `longitude`                | DOUBLE PRECISION |                                                 |
| `unique_id`                | TEXT             | Recent only                                     |
| `establishment_status`     | TEXT             | `Pass`, `Conditional Pass`, `Closed`, …         |
| `min_inspections_per_year` | TEXT             | Historic only                                   |
| `street`                   | TEXT             | Derived from `establishment_address`            |
| `unit`                     | TEXT             | Derived from `establishment_address`            |
| `postal_code`              | TEXT             | Derived; recent only in practice                |

### The `load_log` table

`load_log` records one row per seed or refresh. The pipeline compares its
newest `recent_path` with the newest file in the raw zone to decide whether
to skip.

| Column            | Type        | Notes                                                 |
| ----------------- | ----------- | ----------------------------------------------------- |
| `id`              | SERIAL PK   | Surrogate key                                         |
| `loaded_at`       | TIMESTAMPTZ | Defaults to `now()`                                   |
| `kind`            | TEXT        | `seed` or `refresh`                                   |
| `recent_path`     | TEXT        | For example, `recent/20261012T113012Z/Dinesafe.csv`   |
| `historical_path` | TEXT        | For example, `historical/20261012T113012Z/`; seed only |
| `rows_deleted`    | INTEGER     | Always 0 for a seed                                   |
| `rows_inserted`   | INTEGER     |                                                       |

## Column reconciliation

The table below shows which column in each source feeds each database
column. A dash (—) means that source doesn't provide the column, so the
value is `NULL`.

| DB column                  | Historic CSV                | Recent CSV         |
| -------------------------- | --------------------------- | ------------------ |
| `establishment_id`         | `Establishment ID`          | `estId`            |
| `inspection_id`            | `Inspection ID`             | —                  |
| `establishment_name`       | `Establishment Name`        | `estName`          |
| `establishment_type`       | `Establishment Type`        | —                  |
| `establishment_address`    | `Establishment Address`     | `address`          |
| `infraction_details`       | `Infraction Details`        | `typeDesc`         |
| `infraction_category`      | —                           | `deficiencyDesc`   |
| `inspection_date`          | `Inspection Date`           | `inspectionDate`   |
| `severity`                 | `Severity`                  | `severity`         |
| `action`                   | `Action`                    | —                  |
| `outcome`                  | `Outcome`                   | `OutcomeDesc`      |
| `outcome_date`             | —                           | `OutcomeDate`      |
| `amount_fined`             | `Amount Fined`              | `amountFined`      |
| `latitude`                 | `Latitude`                  | `latitude`         |
| `longitude`                | `Longitude`                 | `longitude`        |
| `unique_id`                | —                           | `unique_id`        |
| `establishment_status`     | `Establishment Status`      | `inspectionStatus` |
| `min_inspections_per_year` | `Min. Inspections Per Year` | —                  |

The importer reads these source columns but doesn't store them:

- **Historic:** `Rec #`.
- **Recent:** `_id`, `phone`, and `observation`. `oldEstId` is used only
  for de-duplication and is then discarded.

<!-- prettier-ignore -->
> [!WARNING]
> The Open Data portal describes `typeDesc` as the category and
> `deficiencyDesc` as the details. The actual data is the other way around. `typeDesc` holds the specific infraction (for
> example, `FAIL TO ENSURE FACILITY SURFACE CLEANED AS NECESSARY - SEC. 22`)
> and `deficiencyDesc` holds the category (for example, `06. MAINTENANCE /
> SANITATION OF SANITARY FACILITIES`). The code maps by content, so
> `typeDesc` fills `infraction_details`. This also means `infraction_details`
> holds the same kind of text in both eras.

<!-- prettier-ignore -->
> [!NOTE]
> The portal's historical data dictionary also lists `Inspection
> Observation`, `Outcome Date`, and `unique_id`. The live ZIP (last modified
> July 6, 2026) doesn't contain them, and `HISTORICAL_COLUMN_MAP` doesn't
> map them. If a future ZIP adds them, the importer drops them.

### Old ID duplicates

From November 2023 to November 2025, the recent feed lists some inspections
twice: once under the old numeric `estId`, and again under a new `estId`
whose `oldEstId` points back to the old one. `drop_old_id_duplicates()`
removes the old-ID copy whenever the same `(oldEstId, inspectionDate)`
appears under a new ID. On the October 14, 2026 download, it drops 3,996 of
121,606 rows, dated from November 13, 2023 to November 7, 2025.

### Address formats

The two feeds format addresses differently. `split_address()` handles both:

| Source   | Format                                     | Example                         |
| -------- | ------------------------------------------ | ------------------------------- |
| Historic | `{STREET}[, {unit}]`, upper case           | `266 EDDYSTONE AVE, Unit-0`     |
| Recent   | `{Street} {unit or None} {postal or None}` | `1871 O'Connor Dr None M4A 1X1` |

A unit is detected by a `Word-` token such as `Unit-`, `Bldg-`, or `Flr-`.
Units without a marker can't be told apart from the street, so they stay in
`street`. If a recent address doesn't end in a postal code or `None`, the
raw value is kept in `street`, and the load logs a count of unparsed
addresses. On the October 14, 2026 download, that count is 0.

## Known inconsistencies

The importer maps columns but doesn't normalize their values. Queries that
cover both eras need to account for these differences:

- **Establishment IDs:** many recent rows use a new Salesforce-style `estId`
  (for example, `001Vo000013QngNIAS`) instead of the numeric ID. Since
  `oldEstId` isn't stored, the database can't link one establishment's
  historic and recent rows.
- **Severity:** a not-applicable severity is `NA - Not Applicable` in the
  historic data but `NA` in the recent data.
- **Outcome:** the recent data uses both `Conviction - Fined` and
  `Conviction: Fined`.
- **Status:** the historical files contain only `Pass` and
  `Conditional Pass`, so every `Closed` result is from November 2023 or
  later. The recent data adds `Temporarily Not Operating`. The app sorts any
  status it doesn't recognize last.
- **Categories:** `infraction_category` uses two schemes. Inspections up to
  November 2025 use values like `5C. Proper maintenance / washing of rooms
  (including washrooms)`, and later ones use values like `05. MAINTENANCE /
  SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT`. Grafana groups by
  the raw value, so the same kind of infraction can appear under two
  labels.
- **Casing:** historic names and addresses are upper case; recent ones are
  mixed case.
- **Era-only columns:** `action`, `establishment_type`, `inspection_id`,
  and `min_inspections_per_year` are `NULL` for recent rows.
  `infraction_category`, `outcome_date`, and `unique_id` are `NULL` for
  historic rows. Grafana works around missing categories with
  `COALESCE(infraction_category, infraction_details)`, and its
  establishment-type panels show historic data only.
- **Types:** `outcome_date`, `amount_fined`, and `min_inspections_per_year`
  are stored as `TEXT`, not as dates or numbers.
