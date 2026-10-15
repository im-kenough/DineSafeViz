# Design decisions - v0.5.0

This page documents design decisions make for `DineSafeViz` `v0.5.0`

## ETL, not ELT

DineSafeViz borrows the layers of the
[medallion architecture](https://learn.microsoft.com/azure/databricks/lakehouse/medallion),
but not its usual pipeline style. Lakehouses are usually ELT. DineSafeViz is
ETL.

### Context

ETL and ELT differ in where the transform runs, not in the order of the
letters. In ETL, a separate engine transforms the data before it reaches the
target. In ELT, the target store transforms the data itself, using its own
compute. For more, see
[Extract, transform, and load](https://learn.microsoft.com/azure/architecture/data-guide/relational-data/etl#extract-load-transform-elt)
on Microsoft Learn.

A medallion lakehouse is ELT. Raw data is loaded into bronze, then Spark or SQL
in the same platform transforms it into silver and gold.

### Decision

DineSafeViz transforms data in the `dsv-pipeline` container, in memory, and
loads finished rows into Postgres:

1. **Extract:** download the CSV and ZIP from Toronto Open Data.
2. **Load:** upload the raw files, unchanged, to Blob Storage (bronze).
3. **Extract:** read the raw files back from Blob.
4. **Transform:** rename columns, normalize values, split addresses, and remove
   duplicates, in Python.
5. **Load:** bulk `COPY` the finished rows into Postgres (silver).

Blob Storage has no compute, and Postgres never transforms data. Because raw
files land before the transform, this is sometimes called *EtLT*. "ETL with a
raw landing zone" is the plainer name.

### Why

- **The target is small.** Postgres runs on a free-tier VM and serves the
  website. Microsoft's guidance is to choose ETL when you need to "offload
  heavy transformations away from a constrained target system."
- **The transform is easy to test.** It's plain Python functions in
  `refresh.py`, covered by unit tests, with no database needed.
- **Least privilege.** The pipeline's database role can only read, insert, and
  delete rows. It doesn't need to create staging tables.
- **Raw data is still kept.** The main benefit of ELT, replaying from raw data,
  comes from the bronze layer, and DineSafeViz has one.

### Costs

- **Reprocessing is coarse.** Historical rows are loaded once. Applying a new
  transform to them means destroying the database volume and seeding again.
- **The transform scales with the VM.** It runs in memory, so a much larger
  dataset would need more memory or a different design.

If these costs grow, the ELT alternative is to load raw rows into a staging
table in Postgres and run the transform as SQL. That would let you reprocess
without rebuilding the database.

## Silver and gold share one database

The medallion pattern usually stores gold as separate, aggregated tables.
DineSafeViz doesn't store gold at all.

- **Decision:** the app and Grafana aggregate the `inspections` table on each
  request. The app caches its home page stats in memory for a short time.
- **Why:** at about 508,000 rows, with an index on `inspection_date`, these
  queries are fast enough. A gold table would need its own refresh logic and
  permissions.
- **Cost:** every view repeats the aggregation. The `dinesafe_app` role's
  10-second query timeout caps the worst case.

## Next steps

- For how the layers and pipelines fit together, see
  [Data architecture](../ref/3-1-data-architecture-v2.md).
