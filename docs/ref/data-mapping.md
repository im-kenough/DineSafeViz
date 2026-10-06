# Data mapping

This page describes how DineSafeViz loads the DineSafe datasets into
PostgreSQL. It covers the database schema, how historic and recent columns
map to one table, and the gaps that remain. For the upstream datasets and
their data dictionaries, see [Data sources](./data-sources.md).

The source of truth is the code:

- `src/dsv-db/init.sql`: roles, table, and index.
- `src/dsv-db/refresh.py`: the seed and refresh logic and the column maps.
- `src/dsv-app/app.py` and
  `src/dsv-analytics/provisioning/dashboards/dinesafe.json`: the queries that
  read the table.

## How the database is created

The database is built in two stages. Postgres creates an empty schema, and
then a one-shot container fills it.

1. `dsv-db` (`postgres:17.10`) starts. On the first start only, when the
   `dsv-db-data` volume is empty, Postgres runs `init.sql` from
   `/docker-entrypoint-initdb.d/`. This script creates:
   - the `inspections` table and an index on `inspection_date`.
   - `dinesafe_app`, a role with `SELECT` only. `dsv-app` and Grafana use
     this role.
   - `dinesafe_migrator`, a role with read and write access. Nothing uses it
     yet: `refresh.py` still connects as the bootstrap superuser
     (`DSV_DB_USER`).
2. `dsv-init-db` runs `refresh.py` once and exits (`restart: "no"`). It
   checks whether `inspections` has any rows:
   - **Empty:** it runs `seed()`, which loads the historical data and then the
     recent data.
   - **Not empty:** it runs `refresh()`, which replaces the recent data.

<!-- prettier-ignore -->
> [!NOTE]
> `init.sql` grants privileges on a database named `dinesafe`. If you set
> `DSV_DB_NAME` to anything else, the grants fail.

<!-- prettier-ignore -->
> [!NOTE]
> On the Azure VMs, `dsv-data.timer` runs `scripts/data.sh <env> --load`
> each business-day morning, which runs `dsv-init-db`. Locally, the refresh
> only runs when `dsv-init-db` runs, for example on `docker compose up`.

### Data sources at runtime

`refresh.py` has no network code. It reads the files under `DSV_DATA_DIR`
(`/data`, the read-only `./data` bind mount) and exits non-zero if
`manifest.json` is missing. `scripts/data.sh` fills `./data` from the
`dinesafe` Blob container; `data.py fetch` fills the container from the
Toronto Open Data CKAN portal (`RECENT_CSV_URL` and `HISTORICAL_ZIP_URL`).
See [App architecture](app-architecture.md#data-path).

- `manifest.json`: each file's name, base64 MD5, size, and row count.

- `Dinesafe.csv`: the recent dataset.
- `dinesafe-historical/*.csv`: the historical files, one per year.

### Seed path

`seed()` runs as a single transaction and commits once at the end:

1. Read the recent CSV and map each row (see
   [Row processing](#row-processing)).
2. Drop duplicate rows filed under an old ID (see
   [Old ID duplicates](#old-id-duplicates)).
3. Take the earliest `inspection_date` in the recent data as the cutoff.
   With the current feed, the cutoff is `2023-11-10`.
4. Load each historical CSV in filename order. Rows dated on or after the
   cutoff are skipped. `dinesafe_hist_2023.csv` runs to `2023-12-29`, so its
   rows from the overlap window are dropped in favor of the recent feed.
5. Bulk-insert the recent rows and commit.

### Refresh path

`refresh()` reads and maps the recent CSV first. Then, in one
transaction, it runs `DELETE FROM inspections WHERE inspection_date >=
cutoff`, inserts the new rows, and commits. Readers never see a partially
loaded table. Historical rows stay in place because they're older than the
cutoff.

### Row processing

`_read_csv_rows()` and `map_row()` apply these steps to every row from
either dataset:

- **Encoding:** decode as UTF-8 (BOM-tolerant), and fall back to cp1252.
  The historical files mix the two.
- **Column mapping:** rename the CSV columns to the unified schema using
  `HISTORICAL_COLUMN_MAP` or `RECENT_COLUMN_MAP`. Any target column that
  the source doesn't provide is set to `NULL`.
- **Nulls:** turn empty strings and the literal string `"None"` into `NULL`.
- **Dates:** convert `MM/DD/YYYY` (used only in `dinesafe_hist_2023.csv`)
  to ISO `YYYY-MM-DD`.
- **Address split:** split `establishment_address` into `street`, `unit`,
  and `postal_code` (see [Address formats](#address-formats)).
- **Insert:** load with `COPY`. Tabs and newlines inside values become
  spaces.

## Schema

All data lives in one denormalized table, `inspections`. Each row is **one
infraction**. An inspection with no infractions is a single row with `NULL`
infraction fields. Nothing in the table identifies an inspection directly,
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
> The recent data dictionary in [Data sources](./data-sources.md) describes
> `typeDesc` as the category and `deficiencyDesc` as the details. The actual
> data is the other way around. `typeDesc` holds the specific infraction (for
> example, `FAIL TO ENSURE FACILITY SURFACE CLEANED AS NECESSARY - SEC. 22`)
> and `deficiencyDesc` holds the category (for example, `06. MAINTENANCE /
> SANITATION OF SANITARY FACILITIES`). The code maps by content, so
> `typeDesc` fills `infraction_details`. This also means `infraction_details`
> holds the same kind of text in both eras.

<!-- prettier-ignore -->
> [!NOTE]
> The historic data dictionary also lists `Inspection Observation`,
> `Outcome Date`, and `unique_id`. The historical CSVs used for testing
> (snapshot from April 11, 2023) don't contain them, and
> `HISTORICAL_COLUMN_MAP` doesn't map them. If the live ZIP includes them,
> the importer drops them.

### Old ID duplicates

From November 2023 to November 2025, the recent feed lists some inspections
twice: once under the old numeric `estId`, and again under a new `estId`
whose `oldEstId` points back to the old one. `drop_old_id_duplicates()`
removes the old-ID copy whenever the same `(oldEstId, inspectionDate)`
appears under a new ID. On the snapshot whose latest inspection is
September 28, 2026, it drops 3,561 of 118,777 rows.

### Address formats

The two feeds format addresses differently. `split_address()` handles both:

| Source   | Format                                     | Example                         |
| -------- | ------------------------------------------ | ------------------------------- |
| Historic | `{STREET}[, {unit}]`, upper case           | `266 EDDYSTONE AVE, Unit-0`     |
| Recent   | `{Street} {unit or None} {postal or None}` | `1871 O'Connor Dr None M4A 1X1` |

A unit is detected by a `Word-` token such as `Unit-`, `Bldg-`, or `Flr-`.
If a recent address doesn't match the expected pattern, the raw value is
kept in `street`, and the refresh logs a count of unparsed addresses.

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
- **Status:** the recent data adds `Temporarily Not Operating`. The app
  sorts any status it doesn't recognize last.
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
