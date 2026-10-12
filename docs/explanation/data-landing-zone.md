# Data landing zone: how DineSafeViz manages its data

This page explains the data landing zone model and how DineSafeViz applies it
to the DineSafe datasets. It covers what a landing zone is, where the
scheduled refresh runs, where the load and transform happen, and what happens
to the data when you restart the Docker Compose stack. It records design
decisions made on October 12, 2026.

<!-- prettier-ignore -->
> [!NOTE]
> This page describes a proposed design. It isn't implemented yet. For the
> pipeline as it runs today, see
> [Dataset download and refresh](dataset-refresh.md).

The short version: raw CSVs land in a private, Entra-only Blob container, a
one-shot job loads them into Postgres, and Postgres serves the app. Nothing
contacts Toronto Open Data except the scheduled timer or a command you run
on purpose.

## Goals

The design aims to make data management simpler while keeping the raw data
secured the way an enterprise would. Specifically:

- Keep the raw data private: Entra ID tokens only, a default-deny storage
  firewall, and role assignments scoped to what each identity needs. No
  private endpoint, because it costs more than this project justifies.
- Remove moving parts that don't add safety.
- Check Toronto Open Data only on the schedule, or when you force a check.
- Never change the data as a side effect of restarting containers.

## How other teams handle this

Most teams that manage data from an outside source follow a similar layout.
The source data lands in private object storage first, and the database is
built from that copy.

```
source ──► [ingest job] ──► raw zone (object storage, private, immutable)
                               │
                               ▼
                         [load/transform] ──► database (rebuildable)
                                                  ▲
                                           app reads only
```

These patterns show up again and again:

- **A raw zone.** Raw files land in private object storage and are never
  edited. This copy is the source of truth, and you can rebuild the database
  from it at any time.
- **One writer, many readers.** A single ingest job writes to the raw zone.
  Everything else gets read-only access.
- **No local mirror.** The loader reads straight from storage. Few teams keep
  a synced copy of the files on disk.
- **Bootstrap from storage or backup.** A new environment fills its database
  from the raw zone or a backup, not by downloading from the source again.
- **Least privilege by identity.** The ingest identity can write raw files,
  the loader can read them and write the database, and the app can only read
  the database.

## What a landing zone is

"Landing zone" means two related things. DineSafeViz uses both.

- **Azure landing zone (platform level).** Separate subscriptions for each
  environment, with identity, network, and policy guardrails. DineSafeViz
  already has this: `sub-dsv-stg01` and `sub-dsv-prod01`, each with its own
  managed identity.
- **Data landing zone (pipeline level).** Data moves through zones, and each
  zone has one job. This is often called the medallion model.

The following table describes each zone of the data landing zone.

| Zone      | Common names     | What's in it                                | Who writes          | Who reads          |
| --------- | ---------------- | ------------------------------------------- | ------------------- | ------------------ |
| Raw       | Landing, bronze  | Files exactly as downloaded, never edited   | Ingest stage only   | Load stage         |
| Transform | Silver           | Rows decoded, mapped, cleaned, and deduped  | Load stage, in memory | Load stage       |
| Serving   | Gold             | Clean, typed tables the app queries         | Load stage, in one transaction | App, read-only |

The medallion model names responsibilities, not a number of tables. Many
teams store the silver zone as its own set of tables. DineSafeViz runs the
silver step in memory, in Python, because the transforms are already written
and tested there. See [The ETL logic](#the-etl-logic).

The main rule is that **the raw zone can rebuild everything after it.** If you
lose the database, ship a bad transform, or bring up a new VM, you replay
from the raw zone. That's why "seed an empty database from Blob" is part of
the design, not just a convenience.

### You don't need a new Azure data product

A landing zone is a way of organizing data, not a product. Large teams often
use Azure Data Factory, Microsoft Fabric, or Databricks, because they manage
dozens of sources and teams. For one CSV a day, those services add cost,
another identity, and more firewall work. For example, Data Factory needs a
managed virtual network or a trusted-service exception to reach a firewalled
storage account.

DineSafeViz builds the same model from parts it already has, as the
following table shows.

| Landing zone part         | Common enterprise choice               | DineSafeViz                            |
| ------------------------- | -------------------------------------- | -------------------------------------- |
| Raw zone                  | Data Lake Storage Gen2, OneLake        | Blob container in `stdsv<env>01`       |
| Scheduler                 | Data Factory, Fabric pipelines, Airflow | `systemd` timer on the VM             |
| Ingest                    | Data Factory copy activity             | `dsv-pipeline ingest`                  |
| Load and transform        | Databricks, dbt, Data Factory data flows | `dsv-pipeline load`, SQL in Postgres |
| Serving                   | Synapse, Azure SQL, Postgres           | `dsv-db`                               |

## Where the scheduled refresh runs

The refresh runs on a `systemd` timer on each VM, not in GitHub Actions. The
storage firewall drives this decision.

GitHub-hosted runners have dynamic IP addresses. To reach a default-deny
storage account, a workflow has to add its current IP as a firewall rule,
upload, and then remove the rule. The workflow identity then needs permission
to change the storage account's network rules. That's a control-plane write,
which is a wider permission than the data-plane "write blobs" role the job
needs. Also, according to
[the Azure Storage firewall limitations](https://learn.microsoft.com/azure/storage/common/storage-network-security-limitations#restrictions-for-ip-network-rules),
IP network rules have no effect on requests from the same Azure region as the
storage account. GitHub runners run on Azure, so a runner in the same region
might not behave as expected.

The VM is already allowed through the firewall by the subnet's service
endpoint, and it gets tokens from its managed identity. It needs no stored
secrets and no firewall changes.

| Concern                  | VM timer                     | GitHub Actions with OIDC                        |
| ------------------------ | ---------------------------- | ----------------------------------------------- |
| Secrets                  | None (managed identity)      | None (OIDC federation)                          |
| Storage firewall         | Already allowed (VNet rule)  | Temporary IP rule; needs network-rule write access |
| Failure visibility       | A `failed` unit on the VM; alerting comes later | GitHub emails you                |
| Runs when the VM is down | No                           | Yes                                             |

GitHub Actions with OIDC is a good pattern when the target accepts public
traffic, or when you run self-hosted runners inside the virtual network.
Neither applies here.

### Each environment ingests its own data

The stg and prod VMs each run the job and write to their own storage account.
This keeps the subscription boundary clean, because prod never depends on
stg. The trade-off is that stg and prod can briefly serve different data if
one fetch fails. Dev reads stg's raw zone with read-only access.

Two alternatives were considered and rejected:

- **Prod ingests, stg reads prod.** This gives one copy of the data, but stg
  would need cross-subscription read access and a firewall rule on prod's
  storage, which couples stg to prod.
- **A shared data subscription.** This is the most enterprise-looking option,
  but it needs a third storage account plus cross-subscription roles and
  firewall rules for both environments.

## Where the load and transform happen

The load runs as a one-shot job next to the database, never inside the web
app. The web app has no code path that writes inspection data.

The job uses ETL (extract, transform, load). It extracts the CSVs from Blob,
transforms the rows in Python, and loads them into Postgres with `COPY`.

```
Blob (dinesafe/recent/20261012T113012Z/Dinesafe.csv)
   │  download into the container
   ▼
Python transform           ← decode, map columns, clean dates and addresses,
   │                         drop duplicates (src/dsv-db/refresh.py)
   ▼
public.inspections         ← DELETE the recent window, COPY new rows,
   │                         in one transaction
   ▼
load_log                   ← same transaction: which blob, how many rows
```

Each step has a reason:

- **Transform in Python, not SQL.** The transforms handle mixed file
  encodings, two date formats, address parsing with regular expressions, and
  duplicate rows. They're pure functions with unit tests in
  `src/dsv-db/tests/test_refresh.py`. Rewriting them in SQL would add risk
  and no benefit.
- **No staging table.** A staging table helps when the transform runs in SQL.
  Here, Python hands finished rows to `COPY`, and the single transaction
  already makes the swap atomic.
- **One transaction.** The app sees either the old data or the new data,
  never a half-loaded table. Postgres readers aren't blocked while the load
  runs.
- **`load_log` makes the load idempotent.** If the newest blob path is already
  in `load_log`, the load does nothing. This replaces the local
  `manifest.json` and stops the reload on every `docker compose up`.
- **Read straight from Blob.** Downloading inside the container removes the
  `./data` folder, the `sync` step, the `.part` files, and the local
  manifest.

### The ETL logic

The load runs the steps below, in order. Everything except the download is
existing code in `src/dsv-db/refresh.py`.

1.  **Extract.** Download the newest `recent/` file, and on a seed, every file
    in the newest `historical/` folder. The recent file is about 45 MB, and
    the loader already reads whole files today.
2.  **Decode.** `decode_csv` tries UTF-8 (with or without a byte order mark)
    and falls back to Windows-1252. DineSafe exports mix the two: older
    yearly files are UTF-8 and newer ones are Windows-1252.
3.  **Map columns.** `map_row` renames each CSV header to an `inspections`
    column. The historical and recent files use different headers, so each
    has its own map, `HISTORICAL_COLUMN_MAP` or `RECENT_COLUMN_MAP`. Columns
    not in a map are dropped: `Rec #` from historical files, and `_id`,
    `phone`, and `observation` from the recent file. The recent feed has no
    action column, so `action` is `NULL` for recent rows.
4.  **Clean values.** `normalize` turns empty strings and the literal text
    `None` into SQL `NULL`.
5.  **Normalize dates.** `normalize_date` converts `MM/DD/YYYY`, used only by
    the 2023 historical file, to `YYYY-MM-DD`, so date comparisons work across
    files.
6.  **Split addresses.** `split_address` splits `establishment_address` into
    `street`, `unit`, and `postal_code`. Recent addresses end in a postal code
    or the text `None`. A unit starts at the first `Word-` token, such as
    `Unit-` or `Bldg-`. Historical addresses use `street, unit`. The loader
    prints how many recent addresses didn't match. A non-zero count means
    Toronto changed the address format, and the raw address stays in
    `street`.
7.  **Drop duplicates (recent file only).** From November 2023 to November
    2025, the recent feed lists some inspections twice: under an old
    establishment ID, and under a new ID whose `oldEstId` points back to the
    old one. `drop_old_id_duplicates` keeps the row under the new ID.
8.  **Find the cutoff.** `min_inspection_date` returns the earliest
    inspection date in the recent file. The recent file covers every
    inspection from that date onward, so it replaces everything in that
    window.
9.  **Load, in one transaction:**
    - **Seed** (the table is empty): `COPY` the historical rows dated before
      the cutoff, then `COPY` the recent rows. Newer historical files overlap
      the recent file's window, and the cutoff stops those inspections from
      being counted twice.
    - **Refresh** (the table has data): `DELETE` every row on or after the
      cutoff, then `COPY` the recent rows. This also picks up corrections and
      backfilled inspections inside the window.
    - Insert a `load_log` row, then commit.

`COPY` writes tab-separated text, so `bulk_insert` replaces tabs, carriage
returns, and newlines inside values with spaces.

For the full column mapping, see [Data mapping](../ref/data-mapping.md).

### Blob layout

Each ingest writes to its own folder, named for its UTC start time, in the
existing `dinesafe` container. Nothing is ever overwritten.

```
stdsvprod01 / dinesafe
  recent/20261012T113012Z/Dinesafe.csv      metadata: source_last_modified=2026-10-12T09:14:00
  recent/20261009T113005Z/Dinesafe.csv
  historical/20261012T113012Z/dinesafe-2001.csv … dinesafe-2023.csv
```

- **Newest.** The newest file is the last folder in a sorted listing of
  `recent/`. Timestamp names sort in time order, so no manifest is needed.
- **Ingest time, not Toronto's date.** If `--force` downloads a file with the
  same `last_modified` but different content, it gets a new folder instead
  of overwriting one.
- **New-data check.** `ingest` compares CKAN's `last_modified` with the
  newest blob's `source_last_modified` metadata. With `--force`, it always
  downloads, but skips the upload when the MD5 matches the newest blob.
- **Historical files.** `ingest` downloads the historical ZIP only when
  `historical/` is empty, or when you pass `--historical`.

### The `load_log` table

`load_log` records every successful load. The load writes the row in the same
transaction as the data, so a failed load rolls back both, and `load_log`
never claims something that didn't happen. Failure details go to the job's
output and the `systemd` journal.

```sql
CREATE TABLE load_log (
    id               SERIAL PRIMARY KEY,
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind             TEXT NOT NULL CHECK (kind IN ('seed', 'refresh')),
    recent_path      TEXT NOT NULL,   -- recent/20261012T113012Z/Dinesafe.csv
    historical_path  TEXT,            -- historical/20261012T113012Z/ (seed only)
    rows_deleted     INTEGER NOT NULL,
    rows_inserted    INTEGER NOT NULL
);
```

`load` decides what to do from `inspections` and `load_log`:

| State                                                    | Action                      |
| -------------------------------------------------------- | --------------------------- |
| `inspections` is empty                                   | Seed                        |
| Newest `recent_path` in `load_log` matches the newest blob | Skip, and print "already current" |
| Otherwise                                                | Refresh                     |
| You pass `--force`                                       | Refresh, even if current    |

### Database role

The pipeline connects as `dinesafe_migrator`, which `src/dsv-db/init.sql`
already defines. It gets `SELECT`, `INSERT`, and `DELETE` on `inspections` and
`load_log`, and nothing else. Today `refresh.py` connects as the Postgres
superuser, so this change also closes an existing least-privilege gap.

## Failure handling and retention

Every failure leaves the database serving its last good load. Because deploys
call only `load`, never `ingest`, an outage at Toronto Open Data can make your
data older but can't break a deploy.

| Failure                                         | What happens                                        | Data served          |
| ----------------------------------------------- | --------------------------------------------------- | -------------------- |
| Toronto Open Data is down, or validation fails  | `ingest` uploads nothing; `run` exits 1              | Last good load       |
| Blob is unreachable (firewall or token)         | `run` or `load` exits 1                              | Last good load       |
| The load fails partway                          | The transaction rolls back: no data change, no `load_log` row | Last good load |
| Nothing new                                     | `run` exits 0                                        | Last good load       |
| Deploy, Blob unreachable, database has data     | `deploy.sh` warns and continues                      | Last good load       |
| Deploy, Blob unreachable, database is empty     | `deploy.sh` fails                                    | Nothing              |

The only exit codes are 0 (success) and 1 (failure). Today's exit code 3,
"fetch failed but existing data loaded," goes away, because a failed ingest no
longer has anything to do with the load.

### Staleness check

If the newest blob's `source_last_modified` is more than 10 days old, `run`
exits 1. Toronto Open Data publishes most business days, so a long gap
usually means the dataset moved or its ID changed. Without this check, the
job would report success every day while the data quietly aged.

### Alerting

Alerting is out of scope for now. A failed run shows as a `failed` unit in
`systemctl status` and in the journal on the VM. A dead man's switch, such
as a healthchecks.io check that the job pings on success, is a good next
step: it catches a job that failed and also a job that never ran.

### Retention

The raw zone keeps a last good copy no matter how long Toronto Open Data stops
publishing:

- **`ingest` prunes `recent/` to the newest 30 folders,** and only after a
  successful upload, so it never deletes the newest one. That's about 1.4 GB.
  Azure lifecycle rules can't express "keep the newest N," and an age-based
  rule would delete the only copy after a long publishing gap.
- **`historical/` is never pruned.**
- **Soft delete keeps deleted blobs for 7 days,** as an undo for mistakes.
- **Blob versioning stays on,** and the lifecycle rule deletes old versions
  after 30 days. Paths are never overwritten, so versions rarely exist. They're
  a safety net.

## Components

The `dsv-data` and `dsv-init-db` containers become one one-shot service,
`dsv-pipeline`, built from the `src/dsv-db` image. It has three subcommands.

| Subcommand | What it does                                      | Needs                         |
| ---------- | ------------------------------------------------- | ----------------------------- |
| `ingest`   | Toronto Open Data to the raw zone in Blob         | Storage token, `egress` network |
| `load`     | Blob to Python transform to `inspections`         | Storage token, database credentials |
| `run`      | `ingest`, then `load`                             | Both                          |

The following diagram shows one run of the job.

```
           07:30 timer, deploy, or your command
                        │
                        ▼
 ┌──────────── dsv-pipeline (one-shot container) ────────────┐
 │ ingest: CKAN package_show → last_modified newer than       │
 │         newest recent/ folder? → download → validate →     │
 │         upload dinesafe/recent/<timestamp>/Dinesafe.csv    │
 │                                                            │
 │ load:   newest recent/ path already in load_log? → skip    │
 │         else download blob → Python transform →            │
 │         DELETE window + COPY into inspections +            │
 │         insert load_log row (1 transaction)                │
 └────────────────────────────────────────────────────────────┘
```

### One container instead of two

Today the work is split across two containers. `dsv-data` holds a storage
token but no database credentials. `dsv-init-db` holds database credentials
but has no network access. Merging them puts both in one container, which is
how most enterprise loaders work: the loader identity reads the raw zone and
writes the database.

The extra exposure is small. The fetch side already parses CSVs from the
internet while it holds a storage write token, and the loader already writes
the `inspections` table. The design limits what the merged container can do:

- It connects as `dinesafe_migrator`, which can write only `inspections`
  and `load_log`, not as the Postgres superuser.
- Its storage token is minted for each run, passed as a mode-600 file, and
  deleted on exit, as it is today.
- It's the only service on both the `egress` and `backend` networks.

Keeping two containers is possible, but they'd have to pass the file through
a temporary volume. That brings back a hop and the plumbing this design
removes.

### What changes and what stays

The following table lists what the design removes.

| Today                                                    | With this design                       |
| -------------------------------------------------------- | -------------------------------------- |
| Two containers, `dsv-data` and `dsv-init-db`             | One container, `dsv-pipeline`          |
| Three hops: Toronto to Blob to `./data` to Postgres      | Two hops: Toronto to Blob to Postgres  |
| `manifest.json`, pinned version IDs, `sync`, `.part` files, `./data` | Date-named Blob paths and `load_log` |
| Downloads 45 MB and reloads about 120,000 rows on every run | Checks `last_modified`; works only when something changed |
| Reloads on every `docker compose up`                     | Loads only when `load_log` says it's needed |
| Hardcoded CKAN resource URLs                             | Resources looked up by name through `package_show` |

These parts stay as they are:

- The Entra-only storage account with shared keys off, the default-deny
  firewall with the VNet rule, and the IMDS block.
- Validation before upload, and the single-transaction table replacement.
- Blob versioning and soft delete, as a safety net against accidental
  overwrites.

## How the database keeps serving

`dsv-pipeline` never serves data. Postgres does, and its data lives in a named
volume. The following table shows how the services split the work.

| Service                    | Lifetime                              | Job                                   |
| -------------------------- | ------------------------------------- | ------------------------------------- |
| `dsv-db` (Postgres)        | Long-running, `restart: unless-stopped` | Serves the data from its named volume |
| `dsv-app`, nginx, Grafana  | Long-running                          | Read from `dsv-db`                    |
| `dsv-pipeline`             | One-shot: starts, writes, exits       | Changes data only when told to        |

Postgres keeps serving while the pipeline runs. The load commits in one
transaction, so the app sees the old rows until the commit and the new rows
after it.

This is the same split Kubernetes uses: a StatefulSet for Postgres, and a Job
or CronJob for ETL. The design carries over to AKS without changing shape.

## Restarting the stack while you develop

`dsv-pipeline` belongs to a Compose profile, so `docker compose up` never
starts it. Restarting or rebuilding the stack doesn't change the data or
contact anything outside your machine.

| You run                                         | Effect on the data                       | Toronto | Blob |
| ----------------------------------------------- | ---------------------------------------- | ------- | ---- |
| `docker compose up -d`, `restart`, or an app rebuild | None; Postgres reopens its volume   | No      | No   |
| `docker compose down`, then `up`                | None; the volume persists                | No      | No   |
| `docker compose down -v`                        | The database is empty until you run a load | No    | No   |

## Triggers

One wrapper script, `scripts/pipeline.sh`, replaces `scripts/data.sh`. It
mints the storage token and runs a subcommand. The following table shows
every way the pipeline starts.

| Trigger                                      | Command                       | Toronto Open Data                                   | Blob to database                              |
| -------------------------------------------- | ----------------------------- | --------------------------------------------------- | --------------------------------------------- |
| Timer on stg and prod, Monday to Friday 07:30 | `pipeline.sh <env> run`      | Checks `last_modified`; downloads only if newer     | Loads only if there's a new file              |
| You force a check                            | `pipeline.sh <env> run --force` | Always downloads and validates; uploads if the content changed | Loads if there's a new file      |
| `deploy.sh stg`, `prod`, or `dev`            | `pipeline.sh <env> load`      | Never                                               | Seeds an empty database; skips if `load_log` is current |
| You, after `down -v` in dev                  | `pipeline.sh dev load`        | Never                                               | Seeds from stg's raw zone                     |
| You force a reload                           | `pipeline.sh <env> load --force` | Never                                            | Reloads the newest file even if it's in `load_log` |

Only the scheduled timer and `run --force` contact Toronto Open Data. Deploys
and dev read only your own raw zone. The "is it current?" check in `load` is
one Blob list call and one `SELECT`, so it's cheap to run on every deploy.

## A week in the life of the pipeline

The following example walks through one week of the pipeline in prod. The
raw zone starts with this layout, where nothing is ever overwritten:

```
stdsvprod01 / dinesafe
  recent/20261009T113005Z/Dinesafe.csv
  historical/20260601T113002Z/dinesafe-2001.csv … dinesafe-2023.csv
```

- **Monday at 07:30.** The timer runs `pipeline.sh prod run`. `package_show`
  reports the recent file was modified on October 12. The newest blob's
  `source_last_modified` is October 9, so the job downloads the file,
  validates it, and uploads `recent/20261012T113012Z/Dinesafe.csv`.
  `load_log` doesn't contain that path, so the job downloads it, transforms
  the rows, replaces the recent window of `inspections` in one transaction,
  and writes a `load_log` row.
- **Tuesday at 07:30.** `package_show` still reports October 12. The job
  skips the download and the load, and finishes
  in seconds.
- **Wednesday at 07:30.** Toronto Open Data returns a file with missing
  columns. Validation fails, so nothing reaches Blob, and the database
  keeps serving October 12. The job exits with an error, and
  `systemctl status dsv-pipeline` shows the unit as `failed`.
- **Friday.** You rebuild the stg VM. `deploy.sh stg` runs
  `pipeline.sh stg load`. The database is empty, so the load replays
  `historical/` and the newest `recent/` folder from stg's raw zone. The site
  comes back without contacting Toronto Open Data.
- **On your workstation.** You run `docker compose down -v` to start fresh,
  then `pipeline.sh dev load`. It reads stg's raw zone with your `az login`
  identity, which has read-only access, and seeds your local database.

## Best practices this design follows

The design applies these practices, which hold for most data pipelines:

- **One writer per zone.** Everything else gets read-only access.
- **Validate before you publish to the raw zone.** Bad data never gets past
  ingest.
- **Keep raw data immutable.** Use date-named paths, versioning, and soft
  delete.
- **Key loads on the source version.** Running a load again does nothing
  harmful.
- **Separate triggers from the job.** The timer, deploys, and an empty
  database all call the same load. Only the reason for running differs.
- **Make it inspectable.** `load_log` reports what's loaded now, and the
  unit's status and journal report what the last run did.
- **Use the same code path in dev.** Dev uses its own identity with read-only
  access.

## Next steps

These documents describe the current pipeline and the infrastructure this
design builds on:

- [Dataset download and refresh](dataset-refresh.md): the current pipeline
  and its costs.
- [App architecture](../ref/app-architecture.md#data-path): the current data
  path and identities.
- [Identity and access management](../ref/iam.md): the Azure roles, storage
  firewall rules, and database roles this design uses.
- [Data mapping](../ref/data-mapping.md): column mapping and the current seed
  and refresh SQL.
