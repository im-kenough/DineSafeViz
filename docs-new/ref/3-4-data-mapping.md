## Data mapping: CSV to database

Two source schemas map into one table. The recent and historical CSVs use
different column names, and each has columns the other lacks. For the source
files themselves, see [Data sources](3-2-data-sources.md).

Seed and refresh run the same row transforms from `src/dsv-db/refresh.py`.
For the load path and the order of the transform steps, see
[Transformations](datapipe-seed.md#transformations).

### Column mapping

Every database column, its source in each CSV, and its transform. A dash (—)
means the source has no such column, so the value is `NULL`.

| DB column                  | Historical CSV              | Recent CSV         | Transform beyond rename and null handling                    |
| -------------------------- | --------------------------- | ------------------ | ------------------------------------------------------------ |
| `id`                       | —                           | —                  | Assigned by `SERIAL` on insert                               |
| `establishment_id`         | `Establishment ID`          | `estId`            | None. Numeric (historical) or `001Vo…` (most recent rows)    |
| `inspection_id`            | `Inspection ID`             | —                  | None                                                         |
| `establishment_name`       | `Establishment Name`        | `estName`          | None                                                         |
| `establishment_type`       | `Establishment Type`        | —                  | None                                                         |
| `establishment_address`    | `Establishment Address`     | `address`          | Kept raw. Also split into the three columns below.          |
| `street`, `unit`, `postal_code` | Derived                | Derived            | `split_address()`                                            |
| `infraction_details`       | `Infraction Details`        | `typeDesc`         | None. The portal swaps `typeDesc` and `deficiencyDesc` descriptions; the code maps by content. |
| `infraction_category`      | —                           | `deficiencyDesc`   | None                                                         |
| `inspection_date`          | `Inspection Date`           | `inspectionDate`   | `MM/DD/YYYY` → `YYYY-MM-DD`, then cast to `DATE`             |
| `severity`                 | `Severity`                  | `severity`         | None                                                         |
| `action`                   | `Action`                    | —                  | None                                                         |
| `outcome`                  | `Outcome`                   | `OutcomeDesc`      | None                                                         |
| `outcome_date`             | —                           | `OutcomeDate`      | None. Stays `TEXT`.                                          |
| `amount_fined`             | `Amount Fined`              | `amountFined`      | None. Stays `TEXT`.                                          |
| `latitude`, `longitude`    | `Latitude`, `Longitude`     | `latitude`, `longitude` | Cast to `DOUBLE PRECISION`                              |
| `unique_id`                | —                           | `unique_id`        | None                                                         |
| `establishment_status`     | `Establishment Status`      | `inspectionStatus` | None                                                         |
| `min_inspections_per_year` | `Min. Inspections Per Year` | —                  | None. Stays `TEXT`, because 35 stored rows hold the letter `O`. |

Source columns that aren't stored:

- **Historical:** `Rec #` (also `Rec #"` in the 2020 to 2022 files, which is
  harmless because it isn't mapped).
- **Recent:** `_id`, `phone`, and `observation`. `oldEstId` is read for
  de-duplication, then dropped.

### De-duplication

`drop_old_id_duplicates()` drops a recent row when another row has `oldEstId`
equal to its `estId`, on the same date, under a different `estId`. That
removes the numeric-ID copy of an inspection: 3,996 rows in the October 14,
2026 data.

### Address split

`split_address()` handles both address formats. Units need a `Word-` marker
in recent addresses; without one, they stay in `street`.

| Raw `establishment_address`        | `street`              | `unit`    | `postal_code` | Why                                              |
| ---------------------------------- | --------------------- | --------- | ------------- | ------------------------------------------------ |
| `1871 O'Connor Dr None M4A 1X1`    | `1871 O'Connor Dr`    | `NULL`    | `M4A 1X1`     | Recent: `None` unit dropped                      |
| `3155 Markham Rd Unit-D1 M1X 0B5`  | `3155 Markham Rd`     | `Unit-D1` | `M1X 0B5`     | Unit starts at the first `Word-` token           |
| `1 Clairtrell Rd 303 M2N 7H6`      | `1 Clairtrell Rd 303` | `NULL`    | `M2N 7H6`     | No marker, so the unit stays in `street`         |
| `102 Fort York Blvd None None`     | `102 Fort York Blvd`  | `NULL`    | `NULL`        | Recent: no unit, no postal code                  |
| `361 SPADINA AVE None M5T 23`      | `361 SPADINA AVE`     | `NULL`    | `M5T 23`      | Truncated postal code kept as is (16 rows)       |
| `2300 YONGE ST, Unit-C1`           | `2300 YONGE ST`       | `Unit-C1` | `NULL`        | Historical: `street, unit`                       |
| `100 WELLINGTON ST W, BOX 220`     | `100 WELLINGTON ST W` | `BOX 220` | `NULL`        | Historical: anything after `, ` is the unit      |

- A recent address that doesn't end in a postal code or `None` stays whole in
  `street`. The load logs a count of these; it's 0 today.

<details>
<summary>Worked example: one recent row, CSV to database</summary>

The first row of the October 14, 2026 `Dinesafe.csv`, run through `map_row()`:

| CSV column         | Raw value                                                   | DB column                 | Stored value                    |
| ------------------ | ----------------------------------------------------------- | ------------------------- | ------------------------------- |
| `_id`              | `1`                                                         | —                         | Dropped                         |
| `unique_id`        | `0e2432862e567ea16f7020ed88c7776c`                          | `unique_id`               | Same                            |
| `estId`            | `001Vo000013QjdPIAS`                                        | `establishment_id`        | Same                            |
| `oldEstId`         | `10752656`                                                  | —                         | De-dupe only, then dropped      |
| `estName`          | `# HASHTAG INDIA RESTAURANT`                                | `establishment_name`      | Same                            |
| `address`          | `1871 O'Connor Dr None M4A 1X1`                             | `establishment_address`   | Same                            |
|                    |                                                             | `street`                  | `1871 O'Connor Dr`              |
|                    |                                                             | `unit`                    | `NULL`                          |
|                    |                                                             | `postal_code`             | `M4A 1X1`                       |
| `inspectionStatus` | `Pass`                                                      | `establishment_status`    | Same                            |
| `phone`            | `4167522786`                                                | —                         | Dropped                         |
| `inspectionDate`   | `2026-04-21`                                                | `inspection_date`         | `2026-04-21` as `DATE`          |
| `observation`      | `One or more minor infractions were observed …`             | —                         | Dropped                         |
| `typeDesc`         | `FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22` | `infraction_details` | Same                       |
| `deficiencyDesc`   | `05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT` | `infraction_category` | Same                  |
| `severity`         | `M - Minor`                                                 | `severity`                | Same                            |
| `OutcomeDate`      | (empty)                                                     | `outcome_date`            | `NULL`                          |
| `OutcomeDesc`      | `None`                                                      | `outcome`                 | `NULL`                          |
| `amountFined`      | (empty)                                                     | `amount_fined`            | `NULL`                          |
| `latitude`         | `43.72198563`                                               | `latitude`                | `43.72198563` as float          |
| `longitude`        | `-79.30349182`                                              | `longitude`               | `-79.30349182` as float         |
| —                  |                                                             | `inspection_id`, `establishment_type`, `action`, `min_inspections_per_year` | `NULL` (historical only) |
| —                  |                                                             | `id`                      | Next `SERIAL` value             |

</details>

### Not normalized

The load maps columns but keeps values as published. Queries that span both
eras must handle these differences.

| Difference          | Historical                          | Recent                                        |
| ------------------- | ----------------------------------- | --------------------------------------------- |
| Establishment ID    | Numeric                             | Mostly `001Vo…`; `oldEstId` isn't stored, so eras can't be linked |
| Severity "NA"       | `NA - Not Applicable`               | `NA`                                          |
| Status values       | `Pass`, `Conditional Pass`          | Adds `Closed`, `Temporarily Not Operating`    |
| Category            | None                                | Two schemes: `5C. …` to November 7, 2025, `05. …` from November 5, 2025 |
| Outcome spelling    | —                                   | `Conviction - Fined` and `Conviction: Fined`  |
| Casing              | Upper case names and addresses      | Mixed case                                    |
| Trailing spaces     | Not trimmed: 44,616 `infraction_details` values | Not trimmed: 24,114 `infraction_details` values |
