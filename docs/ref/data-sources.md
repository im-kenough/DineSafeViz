# Data sources

This page describes the two DineSafe datasets that DineSafeViz loads, where
they come from, and what the files actually contain. For how the columns map
into the database, see [Data mapping](./data-mapping.md).

The facts and counts on this page come from a download on October 14, 2026,
checked with the transforms in `src/dsv-db/refresh.py`.

## The DineSafe package

Toronto Public Health (TPH) publishes DineSafe on Toronto Open Data at
https://open.toronto.ca/dataset/dinesafe/. The package's refresh rate is
"Daily."

There are two datasets:

1. **Recent data:** November 10, 2023 to today, one CSV, republished about
   once per business day.
2. **Historical data:** 2001 to December 29, 2023, one ZIP of yearly CSVs,
   static.

The two datasets overlap from November 10 to December 29, 2023. The load
keeps the recent rows for that window and drops the historical ones. See
[Seed path](./data-mapping.md#seed-path).

Around June 2026, TPH changed the recent dataset's schema and its resource
ID. The historical data still uses the old schema.

### How the pipeline finds the files

`dsv-pipeline ingest` (`src/dsv-db/data.py`) calls CKAN's `package_show` for
the `dinesafe` package and picks resources by exact name and format, not by
ID, so a changed resource ID doesn't break it.

| Resource name              | Format | Used                         | Notes                                                     |
| -------------------------- | ------ | ---------------------------- | --------------------------------------------------------- |
| `Dinesafe.csv`             | CSV    | Yes, the recent data         | Updated each publish                                      |
| `Dinesafe Historical Data` | ZIP    | Yes, the historical data     | Last modified July 6, 2026                                |
| `Dinesafe™.csv`            | CSV    | No                           | A stale copy, last modified July 8, 2026                  |
| `Dinesafe`                 | JSON   | No                           | The CKAN DataStore table behind the recent data           |
| XML and JSON copies        | —      | No                           | `Dinesafe.xml`, `Dinesafe.json`, and their `™` versions    |

<!-- prettier-ignore -->
> [!WARNING]
> `Dinesafe™.csv` has the same name apart from the `™` sign and the same
> columns as `Dinesafe.csv`, but it stopped updating on July 8, 2026. A
> looser name match would load stale data.

Ingest downloads the recent CSV only when its CKAN `last_modified` is newer
than the `source_last_modified` metadata on the newest file in the raw zone.
It downloads the historical ZIP only when the raw zone has no complete
historical folder, or when you pass `--historical`. See
[Data landing zone](../explanation/data-landing-zone.md#the-etl-logic).

## Recent dataset

The recent dataset holds inspection results from November 10, 2023 to the
last business day. Each row is one infraction, and an inspection with no
infractions is one row with `None` in the infraction columns.

On the portal, `Dinesafe.csv` is a file resource
(`datastore_active: false`). The same rows are in a separate DataStore
resource named `Dinesafe` (resource ID
`75dbb3ff-8281-4f03-9de2-bd1214761302`), also available from
`/datastore/dump/<resource id>`.

Each publish replaces the whole file. In the October 14, 2026 download:

- `_id` runs from 1 to 121,606 with no gaps.
- Rows are sorted by establishment name, with a few hundred exceptions, not
  by inspection date or by when TPH added them. The first row is a
  `2026-04-21` inspection and the last is a `2024-04-17` inspection.
- A publish can add inspections dated as far back as November 2023, not
  only the latest ones.

<!-- prettier-ignore -->
> [!NOTE]
> The October 2, 2026 download ordered rows differently: new rows were
> appended at the end with the next `_id` values, sorted by name within each
> batch. Don't rely on `_id` or row order. The load doesn't use either: it
> replaces every row on or after the file's earliest `inspectionDate`.

The file is UTF-8 without a byte order mark (BOM). Missing values are either
empty or the literal string `None`, depending on the column.

### Data dictionary

The following table lists the recent dataset's columns. The descriptions come
from the portal, with corrections where the data disagrees.

| Column             | Description                                                                                                                 |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `_id`              | Row number in the Open Data table. Not stable across publishes.                                                             |
| `unique_id`        | Unique ID for this record, connected to the source data.                                                                    |
| `estId`            | Establishment ID. Either a legacy numeric ID or a new Salesforce-style ID, depending on the system the record lives in.     |
| `oldEstId`         | Legacy establishment ID.                                                                                                    |
| `estName`          | Establishment name.                                                                                                         |
| `address`          | Address of the establishment.                                                                                               |
| `inspectionStatus` | Result of the inspection, for example `Pass`.                                                                               |
| `phone`            | Establishment phone number.                                                                                                 |
| `inspectionDate`   | Date of inspection, `YYYY-MM-DD`.                                                                                           |
| `observation`      | Summary sentence for the inspection.                                                                                        |
| `typeDesc`         | Details of the infraction. The portal says category; see the warning below.                                                 |
| `deficiencyDesc`   | Category of the infraction. The portal says details; see the warning below.                                                 |
| `severity`         | Severity of the infraction.                                                                                                 |
| `OutcomeDate`      | Date of the prosecution outcome, if there was one.                                                                          |
| `OutcomeDesc`      | Description of the outcome, if there was one. Can be `Pending` while an outcome is processed.                               |
| `amountFined`      | Dollar amount of the fine.                                                                                                  |
| `latitude`         | Latitude of the establishment.                                                                                              |
| `longitude`        | Longitude of the establishment.                                                                                             |

<!-- prettier-ignore -->
> [!WARNING]
> The portal swaps the descriptions of `typeDesc` and `deficiencyDesc`.
> `typeDesc` holds the specific infraction, for example `FAIL TO ENSURE
> EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22`. `deficiencyDesc` holds
> the category, for example `05. MAINTENANCE / SANITATION OF NON-FOOD
> CONTACT SURFACES / EQUIPMENT`.

### Observed values

These are the values in the October 14, 2026 download. The table has 121,606
rows, dated from November 10, 2023 to October 13, 2026.

| Column             | Values (row counts)                                                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `inspectionStatus` | `Pass` (101,599), `Conditional Pass` (19,480), `Closed` (525), `Temporarily Not Operating` (2)                                         |
| `severity`         | `None` (44,816), `M - Minor` (43,940), `S - Significant` (23,980), `NA` (5,478), `C - Crucial` (3,392)                                 |
| `OutcomeDesc`      | `None` (121,155), `Pending` (201), `Conviction - Fined` (161), `Conviction: Fined` (76), `Cancelled` (8), `Charges Withdrawn` (4), `Charges Quashed` (1) |
| `estId`            | Salesforce-style, such as `001Vo000013QjdPIAS` (110,664); numeric and equal to `oldEstId` (10,942)                                    |
| `oldEstId`         | Empty or `None` in 5,521 rows                                                                                                          |

Other things to know about the values:

- **Clean inspections:** the 44,816 rows with `severity` `None` also have
  `None` in `typeDesc` and `deficiencyDesc`. These are inspections with no
  infractions.
- **Two category schemes:** inspections up to November 7, 2025 use
  categories like `5C. Proper maintenance / washing of rooms (including
  washrooms)`. Inspections from November 5, 2025 use categories like
  `05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT`.
  There are 37 distinct `deficiencyDesc` values in total.
- **Duplicate inspections:** 3,996 rows dated from November 13, 2023 to
  November 7, 2025 repeat an inspection under the old numeric `estId`. See
  [Old ID duplicates](./data-mapping.md#old-id-duplicates).
- **Addresses:** every address ends in a postal code or `None`, for example
  `1871 O'Connor Dr None M4A 1X1` or `65 Front St W Unit-442 M5J 1E6`.
- **Outcomes:** `OutcomeDate` and `amountFined` are empty, not `None`, when
  there's no outcome.
- **Summaries:** `observation` restates the result, for example `No
  infractions were observed under the Food Premises Regulation during an
  inspection.` The two `Temporarily Not Operating` rows say `No infractions
  found.` but list infractions.

### Sample recent data

The following rows are the first lines of the October 14, 2026 download.

```
_id,unique_id,estId,oldEstId,estName,address,inspectionStatus,phone,inspectionDate,observation,typeDesc,deficiencyDesc,severity,OutcomeDate,OutcomeDesc,amountFined,latitude,longitude
1,0e2432862e567ea16f7020ed88c7776c,001Vo000013QjdPIAS,10752656,# HASHTAG INDIA RESTAURANT,1871 O'Connor Dr None M4A 1X1,Pass,4167522786,2026-04-21,One or more minor infractions were observed under the Food Premises Regulation during an inspection.,FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22,05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT,M - Minor,,None,,43.72198563,-79.30349182
2,d50fd4c7bd6e8104f4edc5f5095b6027,001Vo000013QjdPIAS,10752656,# HASHTAG INDIA RESTAURANT,1871 O'Connor Dr None M4A 1X1,Pass,4167522786,2026-04-21,One or more minor infractions were observed under the Food Premises Regulation during an inspection.,FOOD PREMISE NOT MAINTAINED TO KEEP FOOD-HANDLING ROOM FREE FROM EQUIPMENT NOT REGULARLY USED - SEC. 7(1)(F),05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT,M - Minor,,None,,43.72198563,-79.30349182
```

## Historical dataset

The historical dataset holds inspection results from 2001 to December 29,
2023, in the legacy schema. Each row is one infraction, like the recent data.

On the portal it's a static file resource (`datastore_active: false`): a ZIP
with one CSV per year, `dinesafe_hist_2001.csv` to `dinesafe_hist_2023.csv`,
in a folder named `Dinesafe Historical data/`. The 2001 to 2022 files are
dated April 11, 2023. The 2023 file was replaced on July 4, 2026, and the ZIP
was last modified on July 6, 2026.

The files aren't consistent with each other:

- **Encoding:** the 2001 to 2022 files are UTF-8 with a BOM.
  `dinesafe_hist_2023.csv` is Windows-1252 (cp1252).
- **Dates:** every file uses `YYYY-MM-DD` except `dinesafe_hist_2023.csv`,
  which uses `MM/DD/YYYY`.
- **Headers:** the 2020, 2021, and 2022 files name the first column
  `Rec #"`, with a stray quote. The importer doesn't read that column.

### Data dictionary

The historical files have these columns, in this order:

1. `Rec #`
2. `Establishment ID`
3. `Inspection ID`
4. `Establishment Name`
5. `Establishment Type`
6. `Establishment Address`
7. `Latitude`
8. `Longitude`
9. `Establishment Status`: the result of the inspection. The portal lists
   `Pass`, `Conditional Pass`, and `Closed`.
10. `Min. Inspections Per Year`
11. `Infraction Details`
12. `Inspection Date`
13. `Severity`: `C - Crucial`, `S - Significant`, `M - Minor`, or
    `NA - Not Applicable`.
14. `Action`
15. `Outcome`
16. `Amount Fined`

### Observed values

The 23 files hold 395,626 rows. Across all of them:

- **Status:** only `Pass` (394,157 rows) and `Conditional Pass` (1,469
  rows) appear. No historical row is `Closed`.
- **Severity:** empty (151,156), `M - Minor` (133,456), `S - Significant`
  (86,878), `NA - Not Applicable` (13,151), and `C - Crucial` (10,985).
- **Outcome:** mostly empty. The most common values are
  `Conviction - Fined`, `Pending`, `Charges Withdrawn`, `Cancelled`,
  `Conviction - Suspended Sentence`, `Charges Dismissed`, and
  `Charges Quashed`.
- **2023 overlap:** `dinesafe_hist_2023.csv` runs from January 3 to
  December 29, 2023. Of its 37,836 rows, 4,791 fall on or after November 10,
  2023 and are dropped in favor of the recent data.

### Sample historical data

The following rows are from `dinesafe_hist_2017.csv`.

```
"Rec #","Establishment ID","Inspection ID","Establishment Name","Establishment Type","Establishment Address","Latitude","Longitude","Establishment Status","Min. Inspections Per Year","Infraction Details","Inspection Date","Severity","Action","Outcome","Amount Fined"
"1","9008018","103913052","'K' STORE","Food Store (Convenience/Variety)","99 CARLTON ST","43.66205","-79.37747","Pass","1","","2017-02-14","","","",""
"2","9008018","104078913","'K' STORE","Food Store (Convenience/Variety)","99 CARLTON ST","43.66205","-79.37747","Pass","1","FAIL TO PROVIDE THERMOMETER IN STORAGE COMPARTMENT O. REG  562/90 SEC. 21","2017-10-24","S - Significant","Corrected During Inspection","",""
"3","10500438","104102644","1 PLUS 1 PIZZA","Food Take Out","361 OAKWOOD AVE","43.68725","-79.43842","Pass","2","","2017-12-05","","","",""
"4","10500438","103895923","1 PLUS 1 PIZZA","Food Take Out","361 OAKWOOD AVE","43.68725","-79.43842","Pass","2","","2017-01-20","","","",""
```

## Next steps

- [Data mapping](./data-mapping.md): how these columns map to the
  `inspections` table.
- [Data landing zone](../explanation/data-landing-zone.md): how the pipeline
  ingests and loads these files.
