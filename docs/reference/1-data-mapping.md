# Data mapping

## Data sources

The DineSafe dataset has two parts: current data and historical data.

The City of Toronto Open Data portal offers both as CSV files. The portal
also provides an API.

## Current data

The "[current data](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/eda39233-4791-464e-98e6-094f51a01916/download/Dinesafe.csv)" dataset is updated daily by the City of Toronto. As of 2026-07-24 its rolling window starts 2023-11-10.

> [!NOTE]
> The City changed this feed's column names and content in 2026. `Action`
> (enforcement activity) was dropped entirely — recent inspections have no
> enforcement data. `estId`/`inspectionStatus` are Salesforce-style identifiers
> replacing the old numeric `Establishment ID`. See `RECENT_COLUMN_MAP` in
> `src/dsv-db/refresh.py` for the source of truth this table mirrors.

<details>
<summary>Sample data (3 rows, current schema)</summary>

| _id | unique_id | estId | oldEstId | estName | address | inspectionStatus | phone | inspectionDate | observation | typeDesc | deficiencyDesc | severity | OutcomeDate | OutcomeDesc | amountFined | latitude | longitude |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 168f86274045194142c0e7c381ccb75d | 001Vo000013QjdPIAS | 10752656 | HASHTAG INDIA RESTAURANT | 1871 O'Connor Dr None M4A 1X1 | Pass | 4167522786 | 2024-03-06 | One or more minor infractions were observed. | FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED | 05. MAINTENANCE / SANITATION | M - Minor | | None | | 43.72199 | -79.30349 |
| 2 | d6b83968d597f037799eb07945d261f1 | 001Vo000013QjzHIAS | | #DESI | 65 Front St W Unit-442 M5J 1E6 | Pass | | 2024-03-04 | No infractions were observed. | | | | | | | 43.645275 | -79.380486 |
| 3 | 1207a0bbb785902f3df59027ade39708 | 10817087 | | 000 BLUEPRINT CLUB | 1 BLUE JAYS WAY None M5V 1J4 | Pass | | 2024-07-11 | No infractions were observed. | | | | | | | 43.64168 | -79.39012 |
</details>

### Data dictionary

Raw CSV header names on the left (the City's naming, not ours); the unified
`inspections` DB column each maps to on the right. `_id`, `oldEstId`, `phone`,
and `observation` are parsed but discarded on import — see the note above
`observation` in particular.

| CSV column | DB column | Notes |
| --- | --- | --- |
| _id | *(discarded)* | Open Data row identifier |
| unique_id | unique_id | Composite key; NULL for historical rows |
| estId | establishment_id | |
| oldEstId | *(discarded)* | Legacy numeric establishment ID, superseded by `estId` |
| estName | establishment_name | |
| address | establishment_address | |
| inspectionStatus | establishment_status | Pass / Conditional Pass |
| phone | *(discarded)* | |
| inspectionDate | inspection_date | |
| observation | *(discarded)* | Generic sentence ("One or more minor infractions were observed…"); `deficiencyDesc` is used instead, see below |
| typeDesc | infraction_details | Specific infraction cited (for example, "FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED…") |
| deficiencyDesc | inspection_observation | Infraction category (for example, "05. MAINTENANCE / SANITATION") — chosen over `observation` for consistency with the historical era's `Infraction Details` granularity |
| severity | severity | S - Significant, M - Minor, C - Crucial |
| OutcomeDate | outcome_date | |
| OutcomeDesc | outcome | |
| amountFined | amount_fined | |
| latitude | latitude | |
| longitude | longitude | |

No current-data column maps to `establishment_type` or `action` — the feed
doesn't carry them. Both are always NULL for recent rows; see
[Unified schema](#unified-schema-inspections-table) below.


## Historical data

The [historical dataset](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/c0a5f6b0-534a-47c3-867d-d4b5cc84a656/download/Dinesafe%20Historical%20Data.zip) contains data going back to 2001.

The `src/dsv-db/refresh.py` script downloads the historical ZIP archive at
runtime and extracts one CSV per year, covering 2001 through 2022. This
document covers the files from 2001 to 2015.

In production, `src/dsv-db/refresh.py` downloads and extracts the
historical ZIP directly (no checked-in copy). For local testing, an offline
copy lives in `docs/ref/local-data/dinesafe-historical/` — see
[how to run locally](../how-to/7-run-locally.md). Either way it contains one
CSV per year (`dinesafe_hist_YYYY.csv`), covering 2001 through 2023 (the
City added the 2023 file to the archive sometime before 2026-07-24; it
previously stopped at 2022). The files from 2001 to 2015 are documented
here.

All years share the same 16 column names. The 2023 file has two format
differences from every earlier year, both handled by `refresh.py`:

- **Dates are `MM/DD/YYYY`** (for example `01/03/2023`), not `YYYY-MM-DD`.
  `normalize_date()` converts on ingest so every stored `inspection_date` is
  ISO regardless of source file.
- **Values aren't double-quoted** (2001-2022 quote every field).
  `_read_csv_rows()` uses a real CSV parser either way, so this doesn't
  require special handling — noted here only because it means "no schema
  drift" is no longer literally true.

## Row counts (2001-2015)

| Year | Rows  |
| ---- | ----- |
| 2001 | 6,066 |
| 2002 | 6,352 |
| 2003 | 7,160 |
| 2004 | 7,181 |
| 2005 | 8,642 |
| 2006 | 9,096 |
| 2007 | 10,130 |
| 2008 | 11,666 |
| 2009 | 11,393 |
| 2010 | 14,920 |
| 2011 | 16,624 |
| 2012 | 17,188 |
| 2013 | 20,392 |
| 2014 | 23,160 |
| 2015 | 21,750 |

Row counts include the header line. The 2023 file (not itemized above, out
of this table's 2001-2015 scope) has 37,836 rows in the raw file, but
`refresh.py` drops rows on or after the recent CSV's earliest date before
insert — see [Data gap](#data-gap-none-currently) below — so the actual
number of 2023 rows loaded from this file varies with the recent feed's
current rolling window.

## Historical columns

```markdown
| # | Column                     | Description |
|---|----------------------------|-------------|
| 1 | Rec #                      | Sequential row number within the file (not globally unique) |
| 2 | Establishment ID           | Present in current dataset (as `estId`) |
| 3 | Inspection ID              | **Not in current dataset** — the feed dropped inspection-level IDs |
| 4 | Establishment Name         | Present in current dataset (as `estName`) |
| 5 | Establishment Type         | **Not in current dataset** — always NULL for recent rows |
| 6 | Establishment Address      | Present in current dataset (as `address`) |
| 7 | Latitude                   | Present in current dataset (position differs: col 7 here, col 15 in current) |
| 8 | Longitude                  | Present in current dataset (position differs: col 8 here, col 16 in current) |
| 9 | Establishment Status       | Present in current dataset (as `inspectionStatus`) |
| 10| Min. Inspections Per Year  | **Not in current dataset.** Values: `1`, `2`, `3` |
| 11| Infraction Details         | Present in current dataset (as `typeDesc`) |
| 12| Inspection Date            | Present in current dataset (as `inspectionDate`). Format: `YYYY-MM-DD`, except the 2023 file — see above |
| 13| Severity                   | Present in current dataset (as `severity`) |
| 14| Action                     | **Not in current dataset** — dropped by the City in 2026; always NULL for recent rows |
| 15| Outcome                    | Present in current dataset (as `OutcomeDesc`) |
| 16| Amount Fined               | Present in current dataset (as `amountFined`) |
```

## Schema differences: historical vs. current

| Aspect                       | Historical                       | Current                              |
|------------------------------|----------------------------------|--------------------------------------|
| Row identifier               | `Rec #` (per-file counter)       | `_id` (Open Data DB key) + `unique_id` (composite hash) |
| Establishment Type           | Present                          | **Absent**                           |
| Inspection ID                | Present                          | **Absent**                           |
| Action                       | Present when there's an infraction | **Absent** (dropped by the City in 2026) |
| Establishment Status         | Present (`Pass` / `Conditional Pass`) | Present (as `inspectionStatus`) |
| Min. Inspections Per Year    | Present (`1` / `2` / `3`)        | Absent                               |
| Inspection Observation       | Absent                           | Present when there's an infraction   |
| Outcome Date                 | Absent                           | Present                              |
| Lat/Lon column position      | Columns 7-8                      | Columns 15-16                        |
| All values double-quoted     | Yes, except the 2023 file        | No                                   |

## Nullability patterns

Roughly 34-40% of rows across all years have empty `Infraction Details`,
`Severity`, and `Action`. These represent clean inspections with no
infractions, and the three fields are always empty together.

`Outcome` and `Amount Fined` have values in fewer than 2% of rows,
only when enforcement reached court.

## Enum values (2001-2015)

<details>
<summary>Establishment Status</summary>

- Pass
- Conditional Pass

</details>

<details>
<summary>Severity</summary>

- _(empty — no infraction)_
- C - Crucial
- M - Minor
- NA - Not Applicable
- S - Significant

</details>

<details>
<summary>Action</summary>

- _(empty — no infraction)_
- Closure Order
- Corrected During Inspection
- Education Provided
- Not in Compliance
- Notice to Comply
- Order
- Recommendations
- Summons
- Summons and Health Hazard Order
- Ticket
- Warning Letter

</details>

<details>
<summary>Outcome</summary>

- _(empty — most rows)_
- Cancelled
- Charges Dismissed
- Charges Quashed
- Charges Withdrawn
- Conviction - Fined
- Conviction - Fined & Probationary Order
- Conviction - Ordered to Close by Court
- Conviction - Probationary Order
- Conviction - Suspended Sentence
- Pending

</details>

<details>
<summary>Establishment Type (48 distinct values)</summary>

- Bake Shop
- Bakery
- Banquet Facility
- Boarding / Lodging Home - Kitchen
- Butcher Shop
- Cafeteria - Private Access
- Cafeteria - Public Access
- Chartered Cruise Boats
- Cheese Plant
- Child Care - Catered
- Child Care - Food Preparation
- Church Banquet Facility
- Cocktail Bar / Beverage Room
- College / University Food Services
- Commissary
- Community Kitchen (Meal Program)
- Elementary School Food Services
- Fish Shop
- Flea Market
- Food Bank
- Food Caterer
- Food Court Vendor
- Food Depot
- Food Processing Plant
- Food Store (Convenience/Variety)
- Food Take Out
- Food Vending Facility
- Hospitals & Health Facilities
- Hot Dog Cart
- Ice Cream / Yogurt Vendors
- Ice Cream Plant
- Institutional Food Services
- Locker Plant
- Meat Processing Plant
- Milk Pasteurization Plant
- Mobile Food Preparation Premises
- Nursing Home / Home for the Aged
- Other Educational Facility Food Services
- Private Club
- Refreshment Stand (Stationary)
- Rest Home
- Restaurant
- Retirement Homes(Licensed)
- Retirement Homes(Un-licensed)
- Secondary School Food Services
- Serving Kitchen
- Student Nutrition Site
- Supermarket

</details>

## Import considerations

These constraints apply when you import historical data into the current
DB schema:

- **Column mapping:** `Rec #` has no equivalent in the current schema.
  Generate `_id` and `unique_id` values during import.
- **Missing in current schema:** `Min. Inspections Per Year` needs either a
  new column or a separate table to preserve it — it has no current-data
  equivalent.
- **Missing in historical data:** `Inspection Observation` and
  `Outcome Date` will be null for all historical rows.
- **CSV quoting:** All historical values are double-quoted except the 2023
  file. Use a proper CSV parser (not naive comma-splitting) because
  `Infraction Details` often contains commas.
- **Date format:** the 2023 historical file uses `MM/DD/YYYY`; every other
  year and the current dataset use `YYYY-MM-DD`. Normalize to one format
  before comparing dates across sources — see `normalize_date()` in
  `src/dsv-db/refresh.py`.

## Database schema

### Unified schema (inspections table)

The Postgres `inspections` table merges both historical (2001–2023) and
recent (2023–present, boundary described below) data into a single schema.
Columns absent in a given era's source feed are NULL. Populated fractions
below are as measured against the live dataset on 2026-07-24
(498,004 rows: 390,835 historical, 107,169 recent).

| # | Column                     | Type             | Historical | Recent |
|---|----------------------------|------------------|------------|--------|
| 1 | id                         | SERIAL (PK)      | auto-generated | auto-generated |
| 2 | establishment_id           | TEXT             | 100%       | 100%   |
| 3 | inspection_id              | TEXT             | 100%       | **NULL always** — no equivalent in the current feed |
| 4 | establishment_name         | TEXT             | 100%       | 100%   |
| 5 | establishment_type         | TEXT             | 100%       | **NULL always** — no equivalent in the current feed |
| 6 | establishment_address      | TEXT             | 100%       | 100%   |
| 7 | infraction_details         | TEXT             | ~62% (clean inspections have none) | ~63% |
| 8 | inspection_observation     | TEXT             | NULL always | ~63% |
| 9 | inspection_date            | DATE             | 100%       | 100%   |
| 10| severity                   | TEXT             | ~62%       | ~63%   |
| 11| action                     | TEXT             | ~62%       | **NULL always** — the City dropped this field from the feed in 2026 |
| 12| outcome                    | TEXT             | <1%        | <1%    |
| 13| outcome_date               | TEXT             | NULL always | <1%  |
| 14| amount_fined               | TEXT             | <1%        | <1%    |
| 15| latitude                   | DOUBLE PRECISION | 100%       | 100%   |
| 16| longitude                  | DOUBLE PRECISION | 100%       | 100%   |
| 17| unique_id                  | TEXT             | NULL always | 100%  |
| 18| establishment_status       | TEXT             | 100%       | 100%   |
| 19| min_inspections_per_year   | TEXT             | 100%       | NULL always |

## Data gap: none currently

As of the archive available 2026-07-24, there is no gap: the historical
files now run through **2023-11-09** and the recent feed's rolling window
starts **2023-11-10**. This wasn't always true — the City added a 2023
historical file to the archive sometime before 2026-07-24 (it previously
stopped at 2022-12-30), which also closed a previously-documented ~11-month
gap covering January through early November 2023.

That same 2023 file's tail (through 2023-12-29) overlaps the recent feed's
window (from 2023-11-10). `refresh.py`'s `seed()` handles this by dropping
historical rows on or after the recent feed's earliest date before insert —
without that, every inspection in the overlap would be double-counted (this
was in fact a real bug in this pipeline until fixed on 2026-07-24; see
[journal-97](journal/journal-97.md) for how it was found and fixed).

Because the boundary is derived from the recent feed's *current* rolling
window rather than hardcoded, it will keep tracking correctly if that
window narrows or widens later — but if the City ever ships another
historical file whose tail extends *past* the recent feed's start (rather
than just up to it), or reopens a gap by narrowing the recent feed's
window, that will need re-checking against live data, not assumed from this
doc.

## Data ingestion

The `src/dsv-db/refresh.py` script handles data loading, not `init.sql`.

**Initial seed (empty table):**
1. Downloads the recent Dinesafe.csv and computes the earliest
   `inspection_date` in it (the overlap cutoff).
2. Downloads the historical ZIP, normalizing every `inspection_date` to ISO
   format on parse (handles the 2023 file's `MM/DD/YYYY`), and drops rows on
   or after the cutoff from step 1.
3. Inserts both into the `inspections` table in a single transaction.

**Daily refresh (table has data):**
1. Downloads the recent Dinesafe.csv
2. Derives the delete cutoff from the earliest `inspection_date` in the fresh CSV
3. Deletes all rows at or after that cutoff
4. Inserts the fresh CSV rows
5. All within a single transaction

**Cron example:**
```
0 6 * * * cd /path/to/DineSafeViz && python3 src/dsv-db/refresh.py
```