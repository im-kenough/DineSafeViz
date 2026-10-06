# Data architecture

This document describes the data components of the DineSafeViz
application: where the data comes from, how it's stored, and how each
service consumes it.

## Data services

### Database

The web app and analytics services read from a PostgreSQL
database (`dinesafe`). The `dsv-db` container runs the stock `postgres`
image pinned in `docker-compose.yml` (see [images.md](../images.md) for the
current version) and creates the schema on first boot via
`src/dsv-db/init.sql`.

A one-shot init container (`dsv-init-db`) seeds the database on first
deploy. On subsequent runs it refreshes the recent data window
instead. In the future, a scheduled GitHub Action will automate the
daily refresh.

#### Datasource

The data comes from the City of Toronto Open Data portal as CSV files.
It arrives in two parts:

- **Historical data (2001–2023 as of 2026-07-24):** a ZIP archive
  containing one CSV per year, downloaded from the
  [historical dataset](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/c0a5f6b0-534a-47c3-867d-d4b5cc84a656/download/Dinesafe%20Historical%20Data.zip).
- **Current data (2023–present):** a single CSV refreshed daily by the
  City, downloaded from the
  [current dataset](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/eda39233-4791-464e-98e6-094f51a01916/download/Dinesafe.csv).

> [!NOTE]
> As of 2026-07-24 there's no gap: historical data runs through
> **2023-11-09** and the recent feed picks up **2023-11-10**. This wasn't
> always true and isn't guaranteed to stay true — see
> [Data gap](../data.md#data-gap-none-currently) in the data mapping doc for
> what changed and what `refresh.py` does to avoid double-counting the
> historical/recent overlap this introduced.

See [data mapping](../data.md) for column definitions, sample rows,
and schema differences between the two datasets.

#### Historical data columns

The historical CSVs share 16 columns. `Rec #` is discarded on import. One
column (`Min. Inspections Per Year`) exists only in historical data and is
preserved as a nullable column in the unified schema. The 2023 file (added
to the archive sometime before 2026-07-24) uses `MM/DD/YYYY` dates instead
of `YYYY-MM-DD` and isn't quoted — see [data mapping](../data.md) for how
`refresh.py` handles both.

| Column                    | Example value                   |
|---------------------------|---------------------------------|
| Rec #                     | 1                               |
| Establishment ID          | 9087913                         |
| Inspection ID             | 102069534                       |
| Establishment Name        | TIM HORTONS                     |
| Establishment Type        | Restaurant                      |
| Establishment Address     | 123 MAIN ST                     |
| Latitude                  | 43.65107                        |
| Longitude                 | -79.34702                       |
| Establishment Status      | Pass                            |
| Min. Inspections Per Year | 2                               |
| Infraction Details        | FAIL TO ENSURE FOOD ... SEC. 26 |
| Inspection Date           | 2015-06-10                      |
| Severity                  | S - Significant                 |
| Action                    | Notice to Comply                |
| Outcome                   | *(empty)*                       |
| Amount Fined              | *(empty)*                       |

#### Current data columns

The current CSV has 18 columns as of the City's 2026 schema change. `_id`,
`oldEstId`, `phone`, and `observation` are discarded on import. The feed no
longer carries an establishment-type or enforcement-action column at all —
`establishment_type` and `action` are always NULL for rows loaded from this
source. See [data mapping](../data.md) for the full column-by-column
mapping.

| Column           | Example value                                 |
|------------------|------------------------------------------------|
| _id              | 1                                              |
| unique_id        | 168f86274045194142c0e7c381ccb75d               |
| estId            | 001Vo000013QjdPIAS                             |
| oldEstId         | 10752656                                       |
| estName          | HASHTAG INDIA RESTAURANT                       |
| address          | 1871 O'Connor Dr None M4A 1X1                  |
| inspectionStatus | Pass                                           |
| phone            | 4167522786                                     |
| inspectionDate   | 2024-03-06                                     |
| observation      | One or more minor infractions were observed.   |
| typeDesc         | FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED     |
| deficiencyDesc   | 05. MAINTENANCE / SANITATION                   |
| severity         | M - Minor                                      |
| OutcomeDate      | *(empty)*                                      |
| OutcomeDesc      | None                                           |
| amountFined      | *(empty)*                                      |
| latitude         | 43.72199                                       |
| longitude        | -79.30349                                      |

#### Database schema

- **Database name:** `dinesafe`
- **Table name:** `inspections`
- **Schema source:** `src/dsv-db/init.sql`

| Column                   | Type             | Notes                          |
|--------------------------|------------------|--------------------------------|
| id                       | SERIAL (PK)      | Auto-generated                 |
| establishment_id         | TEXT             | Both eras                      |
| inspection_id            | TEXT             | Historical only (NULL current — feed dropped it) |
| establishment_name       | TEXT             | Both eras                      |
| establishment_type       | TEXT             | Historical only (NULL current — feed dropped it) |
| establishment_address    | TEXT             | Both eras                      |
| infraction_details       | TEXT             | Both eras                      |
| inspection_observation   | TEXT             | Current only (NULL historical) |
| inspection_date          | DATE             | Both eras                      |
| severity                 | TEXT             | Both eras                      |
| action                   | TEXT             | Historical only (NULL current — the City dropped this field from the feed in 2026) |
| outcome                  | TEXT             | Both eras                      |
| outcome_date             | TEXT             | Current only (NULL historical) |
| amount_fined             | TEXT             | Both eras                      |
| latitude                 | DOUBLE PRECISION | Both eras                      |
| longitude                | DOUBLE PRECISION | Both eras                      |
| unique_id                | TEXT             | Current only (NULL historical) |
| establishment_status     | TEXT             | Both eras                      |
| min_inspections_per_year | TEXT             | Historical only (NULL current) |

### DineSafeViz Inspections

The web app is a Flask application (`src/dsv-app/app.py`) that queries
the `inspections` table and renders a day-by-day inspection report.

The user selects a year and quarter from the navigation. The app
queries all inspections within that quarter's date range, groups them
by `inspection_date`, sorts each day's results by severity (Crucial
first, then Significant, Minor, NA, None), and renders them in a table
via the `index.html` Jinja2 template.

Key files:

- `src/dsv-app/app.py` — Flask routes, database queries, date/quarter
  logic, severity sorting, and the Grafana reverse proxy.
- `src/dsv-app/templates/base.html` — shared layout with year/quarter
  navigation.
- `src/dsv-app/templates/index.html` — the inspection results table,
  color-coded by severity.
- `src/dsv-app/templates/home.html` — landing page with aggregate
  stats (total inspections, years of data).
- `src/dsv-app/templates/dashboard.html` — embeds the Grafana
  analytics dashboard via iframe.

The displayed columns per inspection row are: Severity, Infraction
Details, Establishment (name + address), Establishment Type, Action,
Outcome, Outcome Date, and Amount Fined. `Establishment Type` and
`Action` are always blank for inspections from 2023-11-10 onward — the
current Dinesafe feed doesn't carry either field (see
[data mapping](../data.md)).

### DineSafeViz Analytics

The analytics dashboard is a Grafana instance (`dsv-analytics`, see
[images.md](../images.md) for the pinned version) that reads directly
from the PostgreSQL database and renders visualizations. It's embedded
in the Flask app at `/analytics/` via a reverse proxy and is also
accessible directly at `localhost:3000`.

The dashboard ("DineSafe Inspections Metrics") contains panels
organized into sections:

- **Inspection overview:** Total Inspections, Pass/Conditional
  Pass/Closed counts and percentages.
- **Trends:** Inspections Over Time, Inspections by Day of Week.
- **Enforcement:** Inspection enforcement and remediation breakdowns.
- **Severity breakdown:** Dedicated sections for Crucial, Significant,
  and Minor infractions, each with panels for breakdowns by
  Establishment Type, Enforcement Action Type, Infraction Details, and
  Inspection Observations.

> [!NOTE]
> The enforcement and Establishment Type panels only have data through
> 2023-11-09 — both fields are always NULL for current-era inspections
> (2023-11-10 onward) because the source feed dropped them. These
> panels will look increasingly sparse as the historical share of the
> dataset shrinks relative to ongoing current-era inspections.

Key files:

- `src/dsv-analytics/provisioning/datasources/datasource.yml` — the
  dashboard's PostgreSQL data source configuration (connects to
  `dsv-db` using environment variables).
- `src/dsv-analytics/provisioning/dashboards/dashboard.yml` —
  Grafana's dashboard provisioning config (file-based, allows UI
  edits but changes are ephemeral unless exported and committed).
- `src/dsv-analytics/provisioning/dashboards/dinesafe.json` — the
  full dashboard definition, version-controlled as code.

## Data operations

### Data ingestion

Data fetching and loading is handled by `src/dsv-db/refresh.py`. The
script detects whether the `inspections` table is empty and runs
either a full seed or a daily refresh.

**Initial seed (empty table):**

1. Downloads the current `Dinesafe.csv` and computes the earliest
   `inspection_date` in it — this becomes the historical/recent overlap
   cutoff (see [Data gap](../data.md#data-gap-none-currently)).
2. Downloads the historical ZIP archive from the Toronto Open Data
   portal and extracts one CSV per year (2001–2023 as of 2026-07-24).
3. Maps each CSV's headers to the unified schema using
   `HISTORICAL_COLUMN_MAP`, normalizing `inspection_date` to ISO format
   (handles the 2023 file's `MM/DD/YYYY`), and drops rows on or after the
   cutoff from step 1.
4. Maps the current CSV's rows using `RECENT_COLUMN_MAP`.
5. Bulk-inserts all rows via PostgreSQL `COPY` in a single
   transaction.

**Daily refresh (table has data):**

1. Downloads the current `Dinesafe.csv`.
2. Derives a delete cutoff from the earliest `inspection_date` in the
   fresh CSV (so it tracks the upstream data window automatically).
3. Deletes all existing rows at or after that cutoff.
4. Inserts the fresh CSV rows.
5. All within a single transaction so the table is never in a partial
   state.

The `dsv-init-db` container in `docker-compose.yml` runs this script
as a one-shot service on startup (`restart: "no"`).

#### Data sanitization

The following data sanitization is performed before loading into the
database:

- **Null normalization:** The string `"None"` and empty strings are
  converted to Python `None` (SQL `NULL`) by the `normalize()`
  function.
- **COPY-safe escaping:** Tabs (`\t`), carriage returns (`\r`), and
  newlines (`\n`) within data values are replaced with spaces to
  prevent PostgreSQL `COPY` format errors.
- **NULL marker:** `None` values are written as `\N` (the PostgreSQL
  `COPY` null marker) in the tab-separated buffer.
- **Date normalization:** `inspection_date` is converted to ISO
  `YYYY-MM-DD` by `normalize_date()` regardless of source format, so the
  historical/recent overlap cutoff (see [Data ingestion](#data-ingestion)
  above) compares correctly across files.

Future sanitization work:

- [#76](https://github.com/im-kenough/DineSafeViz/issues/76)
- [#11](https://github.com/im-kenough/DineSafeViz/issues/11)
- [#13](https://github.com/im-kenough/DineSafeViz/issues/13)

### Data refresh

A database refresh runs whenever `dsv-init-db` starts and the
`inspections` table already contains data. The refresh replaces the
recent data window (roughly the last ~2 years of current data) in a
single atomic transaction — delete old rows at or after the CSV's
earliest date, then insert the fresh rows. This means the table is
never missing data mid-refresh.

On first deploy (empty table), a full seed runs instead.
