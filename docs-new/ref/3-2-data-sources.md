# Data sources

This page describes the datasets DineSafeViz loads, including their columns,
their values, and the quirks that affect how you read them.

## The DineSafe package

Toronto Public Health (TPH) publishes DineSafe on Toronto Open Data at
https://open.toronto.ca/dataset/dinesafe/. You can download the files from
the website or through the portal's CKAN API, where DineSafe is the `dinesafe`
package.

DineSafeViz combines two datasets from the package:

| Dataset    | Covers                                   | Shape                  | Updates                                 |
| ---------- | ---------------------------------------- | ---------------------- | --------------------------------------- |
| Recent     | November 10, 2023 to the last business day | One CSV              | Replaced about once per business day    |
| Historical | 2001 to December 29, 2023                | One ZIP of yearly CSVs | Static                                  |

- **Different schemas:** the two datasets have different columns. In May
  2026, TPH replaced the recent CSV with a new file in a new schema. The
  historical data still uses the old one.
- **Overlap:** November 10 to December 29, 2023 is in both datasets.
  DineSafeViz keeps the recent rows for that window and drops the historical
  ones. See [Load path](3-6-data-mapping.md#load-path).

### Files in the package

The package lists eight files. DineSafeViz uses two of them.

| File                       | Format | Used for        | Notes                                                     |
| -------------------------- | ------ | --------------- | --------------------------------------------------------- |
| `Dinesafe.csv`             | CSV    | Recent data     | Current file, updated with each publish.                  |
| `Dinesafe Historical Data` | ZIP    | Historical data | Last changed July 6, 2026.                                |
| `Dinesafe™.csv`            | CSV    | Not used        | Old copy of the recent data, frozen on July 8, 2026.      |
| `Dinesafe`                 | JSON   | Not used        | Same rows as `Dinesafe.csv`, served through the CKAN API. |
| XML and JSON copies        | —      | Not used        | `Dinesafe.xml`, `Dinesafe.json`, and their `™` versions.  |

<!-- prettier-ignore -->
> [!WARNING]
> `Dinesafe™.csv` looks like the recent data: the name differs only by the
> `™` sign and the columns are the same. It stopped updating on July 8, 2026,
> so always use `Dinesafe.csv`.

## Recent dataset

The recent dataset is a single CSV, `Dinesafe.csv`, with one row per
infraction.

### File format

- UTF-8, no byte order mark (BOM). Unquoted except where a value needs it.
- Dates are `YYYY-MM-DD`.
- An inspection with no infractions is one row with `None` in `typeDesc`,
  `deficiencyDesc`, and `severity`.
- Missing values are the literal string `None` in most columns, but empty in
  `OutcomeDate` and `amountFined`. The importer treats both as null.
- The file is a CSV resource (`datastore_active: false`). The same rows are in
  the `Dinesafe` DataStore resource (`75dbb3ff-8281-4f03-9de2-bd1214761302`),
  downloadable from `/datastore/dump/<resource id>`.

### Columns

The descriptions come from the portal, corrected where the data disagrees.

| Column             | Description                                                     | Observed values and notes                                                                                                                       |
| ------------------ | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `_id`              | Row number in the Open Data table.                              | 1 to 121,606, no gaps. Not stable across publishes.                                                                                            |
| `unique_id`        | Unique ID for the row.                                          | 32-character hex string. Unique in every row.                                                                                                  |
| `estId`            | Establishment ID.                                               | 18-character Salesforce-style ID, such as `001Vo000013QjdPIAS` (110,664 rows), or a legacy numeric ID equal to `oldEstId` (10,942 rows).       |
| `oldEstId`         | Legacy numeric establishment ID.                                | `None` in 5,521 rows.                                                                                                                           |
| `estName`          | Establishment name.                                             |                                                                                                                                                 |
| `address`          | Address of the establishment.                                   | `<street> <unit or None> <postal code or None>`. See the address gotcha below.                                                                 |
| `inspectionStatus` | Result of the inspection.                                       | `Pass` (101,599), `Conditional Pass` (19,480), `Closed` (525), `Temporarily Not Operating` (2).                                                |
| `phone`            | Establishment phone number.                                     | `None` in the 10,942 rows with a numeric `estId`.                                                                                               |
| `inspectionDate`   | Date of the inspection.                                         | November 10, 2023 to October 13, 2026.                                                                                                          |
| `observation`      | Summary sentence for the inspection.                            | One of five fixed sentences, determined by `inspectionStatus`.                                                                                  |
| `typeDesc`         | Specific infraction. The portal says category.                  | For example, `FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22`. `None` for clean inspections.                               |
| `deficiencyDesc`   | Infraction category. The portal says details.                   | 37 distinct values, including `None`. See the category gotcha below.                                                                            |
| `severity`         | Severity of the infraction.                                     | `None` (44,816), `M - Minor` (43,940), `S - Significant` (23,980), `NA` (5,478), `C - Crucial` (3,392).                                        |
| `OutcomeDate`      | Date of the prosecution outcome.                                | Empty unless there's an outcome (250 rows).                                                                                                     |
| `OutcomeDesc`      | Prosecution outcome.                                            | `None` (121,155), `Pending` (201), `Conviction - Fined` (161), `Conviction: Fined` (76), `Cancelled` (8), `Charges Withdrawn` (4), `Charges Quashed` (1). |
| `amountFined`      | Dollar amount of the fine.                                      | Empty unless there's an outcome (249 rows). Can be `0`.                                                                                         |
| `latitude`         | Latitude of the establishment.                                  | Always present.                                                                                                                                 |
| `longitude`        | Longitude of the establishment.                                 | Always present.                                                                                                                                 |

### Gotchas

These quirks affect anyone who reads or loads the recent data.

- **Swapped descriptions:** the portal swaps the descriptions of `typeDesc`
  and `deficiencyDesc`. `typeDesc` is the specific infraction and
  `deficiencyDesc` is the category.
- **Row order isn't stable:**
  - October 14, 2026: sorted by establishment name, with 229 out-of-order
    rows. The first row is a 2026-04-21 inspection, the last a 2024-04-17
    inspection.
  - October 2, 2026: new rows were appended at the end with the next `_id`
    values, sorted by name within each batch.
  - Don't rely on `_id` or row order. The load uses neither: it replaces
    every row on or after the file's earliest `inspectionDate`.
- **Backfill:** a publish can add inspections dated as far back as November
  2023, not only the latest ones.
- **Duplicate inspections:** 3,996 rows dated November 13, 2023 to November
  7, 2025 repeat an inspection under the old numeric `estId`. The new-ID copy
  has `oldEstId` pointing back to it. The load drops the numeric-ID copy. See
  [Transformations](3-6-data-mapping.md#transformations).
- **Numeric-ID rows:** every row with a numeric `estId` is dated on or
  before November 7, 2025, and has `phone` set to `None`.
- **Status isn't the worst severity:** `inspectionStatus` comes from the
  inspection as a whole. 14,100 `Pass` rows have `S - Significant` severity.
- **`observation` follows status:**
  - `Pass` with no infractions: `No infractions were observed...`
  - `Pass` with infractions: `One or more minor infractions...`
  - `Conditional Pass`: `One or more significant infractions...`
  - `Closed`: `One or more crucial infractions...`
  - `Temporarily Not Operating`: `No infractions found.`, even though both
    rows list infractions.
- **Two category schemes in `deficiencyDesc`:**
  - Up to November 7, 2025: 23 categories like `5C. Proper maintenance /
    washing of rooms (including washrooms)`, plus `A. OPERATOR FAIL TO MEET
    ADMINISTRATIVE REQUIREMENTS OF`, `B. OPERATOR...`, and `D. HEALTH
    PROTECTION AND PROMOTION ACT (Non-compliance`.
  - From November 5, 2025: 9 categories like `05. MAINTENANCE / SANITATION
    OF NON-FOOD CONTACT SURFACES / EQUIPMENT`, plus `ADMINISTRATIVE
    REQUIREMENTS`.
  - The schemes overlap from November 5 to 7, 2025.
- **Addresses:**
  - The unit and postal code slots hold `None` when missing, for example
    `1871 O'Connor Dr None M4A 1X1` or `102 Fort York Blvd None None`.
  - 16 rows have a truncated postal code, for example
    `361 SPADINA AVE None M5T 23`.
- **Outcome spelling:** `Conviction - Fined` and `Conviction: Fined` mean the
  same thing.
- **Severity spelling:** recent rows use `NA`; historical rows use
  `NA - Not Applicable`.

### Sample

The first rows of the October 14, 2026 download:

```
_id,unique_id,estId,oldEstId,estName,address,inspectionStatus,phone,inspectionDate,observation,typeDesc,deficiencyDesc,severity,OutcomeDate,OutcomeDesc,amountFined,latitude,longitude
1,0e2432862e567ea16f7020ed88c7776c,001Vo000013QjdPIAS,10752656,# HASHTAG INDIA RESTAURANT,1871 O'Connor Dr None M4A 1X1,Pass,4167522786,2026-04-21,One or more minor infractions were observed under the Food Premises Regulation during an inspection.,FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22,05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT,M - Minor,,None,,43.72198563,-79.30349182
2,d50fd4c7bd6e8104f4edc5f5095b6027,001Vo000013QjdPIAS,10752656,# HASHTAG INDIA RESTAURANT,1871 O'Connor Dr None M4A 1X1,Pass,4167522786,2026-04-21,One or more minor infractions were observed under the Food Premises Regulation during an inspection.,FOOD PREMISE NOT MAINTAINED TO KEEP FOOD-HANDLING ROOM FREE FROM EQUIPMENT NOT REGULARLY USED - SEC. 7(1)(F),05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT,M - Minor,,None,,43.72198563,-79.30349182
```

## Historical dataset

The historical dataset is a ZIP of 23 yearly CSVs in the legacy schema, with
one row per infraction.

### File format

- **Layout:** `Dinesafe Historical data/dinesafe_hist_2001.csv` to
  `dinesafe_hist_2023.csv`. 395,626 rows in total.
- **Clean inspections:** one row with empty `Infraction Details`, `Severity`,
  and `Action`.
- **Missing values:** empty strings, never `None`.
- **File dates:** 2001 to 2022 are dated April 11, 2023. The 2023 file was
  replaced on July 4, 2026, and the ZIP on July 6, 2026.

The files aren't consistent with each other:

| File                     | Encoding                                  | Date format  | Quoting      | Header quirk             |
| ------------------------ | ----------------------------------------- | ------------ | ------------ | ------------------------ |
| 2001 to 2019             | UTF-8, no BOM (ASCII only)                | `YYYY-MM-DD` | Every value  | None                     |
| 2020, 2021               | UTF-8, no BOM (ASCII only)                | `YYYY-MM-DD` | Every value  | First column is `Rec #"` |
| 2022                     | UTF-8, no BOM                             | `YYYY-MM-DD` | Every value  | First column is `Rec #"` |
| `dinesafe_hist_2023.csv` | Windows-1252 (cp1252), for example `PÈRE` | `MM/DD/YYYY` | Only as needed | None                   |

### Columns

The files have these 16 columns, in this order.

| #   | Column                      | Observed values and notes                                                                                                                                                   |
| --- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `Rec #`                     | Row number. Restarts in each file. Not imported.                                                                                                                            |
| 2   | `Establishment ID`          | Numeric. Same numbering as `oldEstId` in the recent data.                                                                                                                   |
| 3   | `Inspection ID`             | Numeric. Groups the rows of one inspection. No equivalent in the recent data.                                                                                               |
| 4   | `Establishment Name`        |                                                                                                                                                                             |
| 5   | `Establishment Type`        | 58 types, such as `Restaurant`, `Food Take Out`, and `Supermarket`. No equivalent in the recent data.                                                                       |
| 6   | `Establishment Address`     | Street only, such as `99 CARLTON ST`. No postal code.                                                                                                                       |
| 7   | `Latitude`                  | Always present.                                                                                                                                                             |
| 8   | `Longitude`                 | Always present.                                                                                                                                                             |
| 9   | `Establishment Status`      | Result of the inspection: `Pass` (394,157) or `Conditional Pass` (1,469). The portal also lists `Closed`, but no row has it.                                               |
| 10  | `Min. Inspections Per Year` | `2` (237,068), `3` (122,191), `1` (36,330), or the letter `O` (37 rows, all in 2023).                                                                                       |
| 11  | `Infraction Details`        | Specific infraction. Empty for clean inspections. No category column.                                                                                                       |
| 12  | `Inspection Date`           | See the date format in the file table.                                                                                                                                      |
| 13  | `Severity`                  | Empty (151,156), `M - Minor` (133,456), `S - Significant` (86,878), `NA - Not Applicable` (13,151), `C - Crucial` (10,985).                                               |
| 14  | `Action`                    | Most common: `Notice to Comply` (186,568), empty (151,156), `Corrected During Inspection` (54,418), `Ticket` (2,434), `Summons` (550). No equivalent in the recent data. |
| 15  | `Outcome`                   | Empty in 392,719 rows. Most common: `Conviction - Fined` (1,621), `Pending` (773), `Charges Withdrawn` (284), `Cancelled` (119). 12 distinct values.                      |
| 16  | `Amount Fined`              | Dollars, such as `60`, `62.5`, or `120`. Can be `0`.                                                                                                                        |

### Gotchas

These quirks affect anyone who reads or loads the historical data.

- **Mixed encodings and date formats:** decode and parse each file on its
  own. See the file table.
- **2023 overlap:** `dinesafe_hist_2023.csv` runs from January 3 to December
  29, 2023. 4,791 of its 37,836 rows fall on or after November 10, 2023 and
  are dropped in favor of the recent data.
- **No `Closed` status:** historical closures don't appear, so closure counts
  start in November 2023.
- **Non-numeric minimum inspections:** 37 rows in 2023 have the letter `O`,
  not a number, in `Min. Inspections Per Year`.
- **Rows aren't sorted by date** within a file.
- **Schema differences from the recent data:**
  - Only in historical: `Inspection ID`, `Establishment Type`, `Action`,
    `Min. Inspections Per Year`.
  - Only in recent: infraction category (`deficiencyDesc`), `OutcomeDate`,
    `phone`, `observation`, postal code.

### Sample

Rows from `dinesafe_hist_2017.csv`:

```
"Rec #","Establishment ID","Inspection ID","Establishment Name","Establishment Type","Establishment Address","Latitude","Longitude","Establishment Status","Min. Inspections Per Year","Infraction Details","Inspection Date","Severity","Action","Outcome","Amount Fined"
"1","9008018","103913052","'K' STORE","Food Store (Convenience/Variety)","99 CARLTON ST","43.66205","-79.37747","Pass","1","","2017-02-14","","","",""
"2","9008018","104078913","'K' STORE","Food Store (Convenience/Variety)","99 CARLTON ST","43.66205","-79.37747","Pass","1","FAIL TO PROVIDE THERMOMETER IN STORAGE COMPARTMENT O. REG  562/90 SEC. 21","2017-10-24","S - Significant","Corrected During Inspection","",""
"3","10500438","104102644","1 PLUS 1 PIZZA","Food Take Out","361 OAKWOOD AVE","43.68725","-79.43842","Pass","2","","2017-12-05","","","",""
"4","10500438","103895923","1 PLUS 1 PIZZA","Food Take Out","361 OAKWOOD AVE","43.68725","-79.43842","Pass","2","","2017-01-20","","","",""
```
