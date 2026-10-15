# Data architecture

This page gives a high-level view of how DineSafeViz stores, moves, and serves
DineSafe inspection data.

## Overview

The key data-related tasks of DineSafeViz are to:
1. Perform initial ingest of raw datasets from the Toronto Open Data Portal (TODP)
2. Perform periodic checks to download updated data from the TODP
3. Convert raw data into finished inspection reports and dashboards

The application needs to handle:
1. Fresh application deployment
2. Application redeployment

## Medallion architecture

DineSafeViz adapts the
[medallion architecture](https://learn.microsoft.com/azure/databricks/lakehouse/medallion), sorting data into layers, with each layer more refined.

| Medallion layer | Function                                  | DineSafeViz Component                                                                   |
| --------------- | ----------------------------------------- | ----------------------------------------------------------------------------- |
| Bronze          | Raw data, exactly as the source sent it   | Azure Blob container `dinesafe`, the *raw zone*                                     |
| Silver          | Cleaned, validated, de-duplicated rows    | Postgres container `inspections` table, the *serving zone*                              |
| Gold            | Aggregated, ready for a specific consumer | Not stored. The app and the inspections dashboard (Grafana) aggregate on page read |

Modifications:

- **Two stored layers, not three.** Silver and gold share one Postgres
  database. At about 508,000 rows, query-time aggregation is fast enough, so a
  separate gold table isn't needed.
- **ETL, not ELT.** Lakehouses usually transform data inside the platform that
  stores it. DineSafeViz transforms data in the `dsv-pipeline` container, then
  loads finished rows into Postgres. Postgres never transforms data.

## Pipelines

There are three pipelines: `ingest`, `seed`, and `refresh`. The timer, a
deploy, or an operator starts them.

All three run from `scripts/pipeline.sh <env> <command>`. It gets a storage
token on the host, then starts the one-shot `dsv-pipeline` container, which
runs `pipeline.py <command>`. The command decides which pipelines run:

| Command  | Runs                                         | Started by                                    |
| -------- | -------------------------------------------- | --------------------------------------------- |
| `run`    | `ingest`, then the load step, then freshness | `dsv-pipeline.timer` → `dsv-pipeline.service` |
| `load`   | The load step: `seed`, `refresh`, or skip    | `scripts/deploy.sh`, on every deploy          |
| `ingest` | `ingest` only                                | An operator, by hand                          |

The load step picks `seed` or `refresh` on its own, from the state of the
database:

| Pipeline  | From → to        | Contacts TODP? | Runs when                     | Code                                        |
| --------- | ---------------- | ----------------- | ----------------------------- | ------------------------------------------- |
| `ingest`  | Toronto → bronze | Yes               | `run` or `ingest`             | `data.py: ingest`                           |
| `seed`    | Bronze → silver  | No                | Load step, table is empty or Blob has a new historical folder | `pipeline.py: load` → `loader.py: seed`    |
| `refresh` | Bronze → silver  | No                | Load step, newest file in Blob not loaded yet (or `--force`) | `pipeline.py: load` → `loader.py: refresh` |

All code paths are under `src/dsv-pipeline/`.

In `run`, each step only starts if the one before it succeeded. If ingest
fails, the load and the freshness check don't run.

### Ingest: pull data into the bronze layer

The `ingest` pipeline copies new files from Toronto Open Data to the raw zone
in Azure Blob Storage. It never touches the database.

- Runs from the timer's `run`, or by hand with `pipeline.sh <env> ingest`.
  Deploys never ingest, and only stg and prod can ingest.
- Downloads only when Toronto has a newer file, validates every file, and
  uploads to a new timestamped folder. It keeps the newest 30 recent
  folders.

For details, see [Ingest pipeline](datapipe-ingest.md).

### Seed: initial full load of the silver layer

The `seed` pipeline fully loads the `inspections` table from the raw zone.
The load step runs it whenever the table is empty, so a fresh deployment
triggers a seed. It also reseeds when Blob has a newer complete historical
folder than the last seed used.

- Empties the table, then loads the historical data up to the start of the
  recent CSV, then the recent CSV, in one transaction. If it fails, the table
  keeps the rows it had.
- Streams rows into `COPY`, so a full seed peaks at about 121 MiB.
- Needs a filled raw zone: ingest before the first deploy.

For details, see [Seed pipeline](datapipe-seed.md).

### Refresh: keep the silver layer current

The `refresh` pipeline replaces the recent rows with the newest recent file.
The timer runs it on weekday mornings, right after ingest, and every redeploy
runs it too.

- Replaces only the recent window: every row on or after the earliest
  `inspection_date` in the newest recent CSV. Older rows are never touched
  again.
- The swap is atomic. Visitors see the old data until `COMMIT`, and any
  failure leaves the last good load in place.
- If the newest blob is already loaded, the load step skips.

For details, see [Refresh pipeline](datapipe-refresh.md).

## Operational events

What happens to each layer when you deploy, redeploy, or restart the app?

Deploys, redeploys, and restarts don't add layers. They're events that run
some of the pipelines, or none. Deploys never contact Toronto Open Data: they
only load from the raw zone.

<!-- prettier-ignore -->
> [!IMPORTANT]
> When setting up a new stg or prod environment, you must ingest before the first deploy.
> Run `scripts/pipeline.sh <env> ingest`, then `scripts/deploy.sh`. dev
> loads from stg's raw zone, so stg must be ingested first.

| Event                          | Bronze (Blob)                 | Silver (Postgres)                                                            |
| ------------------------------ | ----------------------------- | ---------------------------------------------------------------------------- |
| First deploy, empty raw zone   | Untouched                     | Schema created. The load fails, and the deploy fails with an empty database. |
| First deploy, raw zone filled  | Read only                     | Schema created, then **seed**.                                               |
| Redeploy                       | Read only                     | Migrations rerun. Then **seed** if Blob has a new historical folder, **refresh** if it has a newer recent file, otherwise skip. |
| Restart or `docker compose up` | Untouched                     | Untouched. The pipeline isn't started by `up`.                               |
| Scheduled run                  | New folder if Toronto changed | **Seed**, **refresh**, or skip, then the staleness check.                    |
| Database volume destroyed      | Untouched                     | Lost. The next deploy is a first deploy, so it seeds from the raw zone.      |

- Postgres runs `init.sql` the first time `dsv-db` starts on an empty volume.
  On every deploy, `deploy.sh` applies the migrations, then runs the load
  step. `deploy.sh` is the only place migrations run, so they must be
  idempotent.
- If a redeploy's load fails, the deploy prints a warning and the site keeps
  serving the data it already has.
- If the timer fires during a deploy, the load lock makes one load wait for the
  other. The second load then finds the file already in `load_log` and skips.

For details, see [Seed pipeline](datapipe-seed.md) and
[Refresh pipeline](datapipe-refresh.md).

## Known limits

These limits follow from the design. They matter most while you're changing
the pipeline in stg.

- **Transform changes don't reach historical rows.** A refresh only replaces
  the recent window. If you change the transform, rows before the recent
  CSV's earliest date (currently November 10, 2023) keep the old logic. To
  reprocess everything, reseed: run `pipeline.sh <env> ingest --historical`,
  or destroy the database volume and redeploy.
- **No down migrations.** Migrations only move forward. Rolling back to an
  older image runs old code against the newer schema.
- **Limited replay window.** The raw zone keeps the newest 30 recent folders,
  so you can't rebuild from a recent file older than that.
- **Environments can differ.** stg and prod each ingest on their own, and dev
  reads stg's raw zone. Before you compare environments, check `load_log` in
  each one.

## Out of scope

Disaster recovery isn't covered yet. The raw zone can rebuild the database,
but losing the storage account itself has no recovery plan.
