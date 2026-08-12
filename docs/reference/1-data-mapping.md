# Data mapping

## Data sources

The DineSafe dataset has two parts: current data and historical data.

The City of Toronto Open Data portal offers both as CSV files. The portal
also provides an API.

## Current data

The City of Toronto updates the "[current data](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/eda39233-4791-464e-98e6-094f51a01916/download/Dinesafe.csv)" dataset daily. It contains about 3 years of data.


<details>
<summary>Sample data (8 rows)</summary>

| _id | Establishment ID | Inspection ID | Establishment Name | Establishment Type | Establishment Address | Infraction Details | Inspection Observation | Inspection Date | Severity | Action | Outcome | Outcome Date | Amount Fined | Latitude | Longitude | unique_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 10752656 | None | # HASHTAG INDIA RESTAURANT | Food Take Out | 1871 O'CONNOR DR None M4A 1X1 | FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22 | One or more minor infractions were observed under the Food Premises Regulation during an inspection. | 2024-03-06 | M - Minor | Notice to Comply | None |  |  | 43.72199 | -79.30349 | 168f86274045194142c0e7c381ccb75d |
| 2 | 001Vo000013QjzHIAS | None | #DESI | Food Take Out | 65 Front St W Unit-442 M5J 1E6 | FOOD PREMISE NOT MAINTAINED WITH CLEAN WALLS IN FOOD-HANDLING ROOM - SEC. 7(1)(G)   | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-03-04 | M - Minor | Notice to Comply | None |  |  | 43.645275 | -79.380486 | d6b83968d597f037799eb07945d261f1 |
| 3 | 10817087 | None | 000 BLUEPRINT CLUB | Food Take Out | 1 BLUE JAYS WAY None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-07-11 | None | None | None |  |  | 43.64168 | -79.39012 | 1207a0bbb785902f3df59027ade39708 |
| 4 | 001Vo000013QnH0IAK | None | 000 CLOVER BANNER CLUB KITCHEN | Food Take Out | 1 Blue Jays Way None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-07-04 | None | None | None |  |  | 43.64168 | -79.39012 | 0800ecf1e1ba903a76ac7badb1d754a3 |
| 5 | 001Vo000013Qhj7IAC | None | 000 MEZZ PRODUCTION KITCHEN (PK) | Commissary | 1 Blue Jays Way None M5V 1J4 | FOOD PREMISE NOT MAINTAINED WITH FOOD HANDLING ROOM IN SANITARY CONDITION - SEC. 7(1)(E)  | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-04-11 | M - Minor | Notice to Comply | None |  |  | 43.64168 | -79.39012 | ee0f219eedadbb3580ace8aaff396397 |
| 6 | 10817088 | None | 000 TD LOUNGE | Food Take Out | 1 BLUE JAYS WAY None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-07-04 | None | None | None |  |  | 43.64168 | -79.39012 | 699cf64aa42c1ee0e6fe5b767703ce81 |
| 7 | 001Vo000013QnGiIAK | None | 000 THE WAREHOUSE (docks) | Commissary | 1 Blue Jays Way None M5V 1J4 | None | No infractions were observed under the Food Premises Regulation during an inspection. | 2024-08-09 | None | None | None |  |  | 43.64168 | -79.39012 | e605e36388c6fbe5176dd514ac5e5949 |
| 8 | 001Vo000013QnGcIAK | None | 000F BLUEPRINT CLUB KITCHEN | Banquet Facility | 1 Blue Jays Way None M5V 1J4 | FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22 | One or more minor infractions were observed under the Food Premises Regulation during an inspection. | 2025-03-27 | M - Minor | Notice to Comply | None |  |  | 43.64168 | -79.39012 | 8bd58999ca6747cebd449e81a9198ac0 |
</details>

### Data dictionary

The following table defines each column.

| Column | Description |
| --- | --- |
| _id | Unique row identifier for Open Data database |
| Establishment ID | Unique identifier for an establishment |
| Inspection ID | Unique ID for an inspection |
| Establishment Name | Business name of the establishment |
| Establishment Type | Establishment type (for example, restaurant, mobile cart) |
| Establishment Address | Municipal address of the establishment |
| Infraction Details | Description of the infraction |
| Inspection Observation | Details observed associated with the infraction |
| Inspection Date | Calendar date the inspection was conducted |
| Severity | Level of the infraction (S - Significant, M - Minor, C - Crucial) |
| Action | Enforcement activity based on the infractions noted during a food safety inspection |
| Outcome | The registered court decision resulting from the issuance of a ticket or summons for outstanding infractions to the Health Protection and Promotion Act |
| Outcome Date | The date of the court outcome |
| Amount Fined | Fine determined in the court outcome |
| Latitude | Latitude of establishment |
| Longitude | Longitude of establishment |
| unique_id | Unique composite key |


## Historical data

The [historical dataset](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b6b4f3fb-2e2c-47e7-931d-b87d22806948/resource/c0a5f6b0-534a-47c3-867d-d4b5cc84a656/download/Dinesafe%20Historical%20Data.zip) contains data going back to 2001.

The `src/dsv-db/refresh.py` script downloads the historical ZIP archive at
runtime and extracts one CSV per year, covering 2001 through 2022. This
document covers the files from 2001 to 2015.

All years share the same 16-column schema, with no schema drift across the
historical files.

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

Row counts include the header line.

## Historical columns

```markdown
| # | Column                     | Description |
|---|----------------------------|-------------|
| 1 | Rec #                      | Sequential row number within the file (not globally unique) |
| 2 | Establishment ID           | Same as current dataset |
| 3 | Inspection ID              | Same as current dataset |
| 4 | Establishment Name         | Same as current dataset |
| 5 | Establishment Type         | Same as current dataset |
| 6 | Establishment Address      | Same as current dataset |
| 7 | Latitude                   | Same as current dataset (position differs: col 7 here, col 15 in current) |
| 8 | Longitude                  | Same as current dataset (position differs: col 8 here, col 16 in current) |
| 9 | Establishment Status       | **Not in current dataset.** Values: `Pass`, `Conditional Pass` |
| 10| Min. Inspections Per Year  | **Not in current dataset.** Values: `1`, `2`, `3` |
| 11| Infraction Details         | Same as current dataset |
| 12| Inspection Date            | Same as current dataset. Format: `YYYY-MM-DD` |
| 13| Severity                   | Same as current dataset |
| 14| Action                     | Same as current dataset |
| 15| Outcome                    | Same as current dataset |
| 16| Amount Fined               | Same as current dataset |
```

## Schema differences: historical vs. current

| Aspect                       | Historical (2001-2015)           | Current                              |
|------------------------------|----------------------------------|--------------------------------------|
| Row identifier               | `Rec #` (per-file counter)       | `_id` (Open Data DB key) + `unique_id` (composite hash) |
| Establishment Status         | Present (`Pass` / `Conditional Pass`) | Absent                          |
| Min. Inspections Per Year    | Present (`1` / `2` / `3`)        | Absent                               |
| Inspection Observation       | Absent                           | Present                              |
| Outcome Date                 | Absent                           | Present                              |
| Lat/Lon column position      | Columns 7-8                      | Columns 15-16                        |
| All values double-quoted     | Yes                              | No                                   |

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
- **Missing in current schema:** `Establishment Status` and
  `Min. Inspections Per Year` need either new columns or a separate
  table to preserve them.
- **Missing in historical data:** `Inspection Observation` and
  `Outcome Date` are null for all historical rows.
- **CSV quoting:** The historical files double-quote all values. Use a
  proper CSV parser, not naive comma-splitting, because
  `Infraction Details` often contains commas.

## Database schema

### Unified schema (inspections table)

The Postgres `inspections` table merges both historical (2001–2022) and
recent (2023–present) data into a single schema. It preserves two columns
from the historical dataset, and columns absent in a given era are NULL.

| # | Column                     | Type             | Historical (2001–2022) | Recent (2023–present) |
|---|----------------------------|------------------|------------------------|-----------------------|
| 1 | id                         | SERIAL (PK)      | auto-generated         | auto-generated        |
| 2 | establishment_id           | TEXT             | populated              | populated             |
| 3 | inspection_id              | TEXT             | populated              | populated             |
| 4 | establishment_name         | TEXT             | populated              | populated             |
| 5 | establishment_type         | TEXT             | populated              | populated             |
| 6 | establishment_address      | TEXT             | populated              | populated             |
| 7 | infraction_details         | TEXT             | populated              | populated             |
| 8 | inspection_observation     | TEXT             | NULL                   | populated             |
| 9 | inspection_date            | DATE             | populated              | populated             |
| 10| severity                   | TEXT             | populated              | populated             |
| 11| action                     | TEXT             | populated              | populated             |
| 12| outcome                    | TEXT             | populated              | populated             |
| 13| outcome_date               | TEXT             | NULL                   | populated             |
| 14| amount_fined               | TEXT             | populated              | populated             |
| 15| latitude                   | DOUBLE PRECISION | populated              | populated             |
| 16| longitude                  | DOUBLE PRECISION | populated              | populated             |
| 17| unique_id                  | TEXT             | NULL                   | populated             |
| 18| establishment_status       | TEXT             | populated              | NULL                  |
| 19| min_inspections_per_year   | TEXT             | populated              | NULL                  |

## Data gap: Jan–Nov 2023

The historical archive (published 2023-04-11) covers through 2022-12-30.
The recent CSV's rolling window currently starts at 2023-11-10. Neither
source covers **2023-01-01 through 2023-11-09** (~11 months) because Toronto
Open Data never published this range in either dataset.

## Data ingestion

The `src/dsv-db/refresh.py` script handles data loading, not `init.sql`.

**Initial seed (empty table):**
1. Downloads the historical ZIP (2001–2022 CSVs)
2. Downloads the recent Dinesafe.csv (2023–present)
3. Inserts both into the `inspections` table in a single transaction

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