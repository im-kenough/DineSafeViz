# Data architecture

This page gives a high-level view of how DineSafeViz stores, moves, and serves
DineSafe inspection data.

## Overview

The key data related tasks of DineSafeViz is to:
1. Perform initial ingest of raw datasets from the Toronto Open Data Portal
2. Perform periodic checks to download updated data from the Toronto Data Portal
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
| Gold            | Aggregated, ready for a specific consumer | Not stored. The app and the inspections dashboard (Grafana) aggregates on page read |

Modifications:

- **Two stored layers, not three.** Silver and gold share one Postgres
  database. At about 508,000 rows, query-time aggregation is fast enough, so a
  separate gold table isn't needed.
- **ETL, not ELT.** Lakehouses usually transform data inside the platform that
  stores it. DineSafeViz transforms data in the `dsv-pipeline` container, then
  loads finished rows into Postgres. Postgres never transforms data.

## Pipelines

Three pipelines move data between the layers. `ingest` fills bronze. `seed` and
`refresh` fill silver from bronze. They're separate steps, and only the
scheduled run does both.

Every pipeline runs through one entry point:
`scripts/pipeline.sh <env> <command>`. It gets a storage token on the host, then starts the one-shot
`dsv-pipeline` container, which runs `pipeline.py <command>`. The command
decides which pipelines run:

| Command  | Runs                                         | Started by                                    |
| -------- | -------------------------------------------- | --------------------------------------------- |
| `run`    | `ingest`, then the load step, then freshness | `dsv-pipeline.timer` → `dsv-pipeline.service` |
| `load`   | The load step: `seed`, `refresh`, or skip    | `scripts/deploy.sh`, on every deploy          |
| `ingest` | `ingest` only                                | An operator, by hand                          |

The load step picks `seed` or `refresh` on its own, from the state of the
database:

| Pipeline  | From → to        | Contacts Toronto? | Runs when                     | Code                                        |
| --------- | ---------------- | ----------------- | ----------------------------- | ------------------------------------------- |
| `ingest`  | Toronto → bronze | Yes               | `run` or `ingest`             | `data.py: ingest`                           |
| `seed`    | Bronze → silver  | No                | Load step, table is empty     | `pipeline.py: load` → `refresh.py: seed`    |
| `refresh` | Bronze → silver  | No                | Load step, newer file in Blob | `pipeline.py: load` → `refresh.py: refresh` |

All code paths are under `src/dsv-db/`.

### Ingest: Toronto Open Data to bronze

Ingest copies new files from Toronto Open Data to Blob Storage. It never
touches the database.

- **Run by:** `dsv-pipeline.timer` (`pipeline.sh <env> run`), or by hand with
  `scripts/pipeline.sh <env> ingest`. Deploys never ingest.

```mermaid
flowchart LR
    start(["ingest"]) --> ask["Ask Toronto's catalog<br/>when files last changed"]
    ask --> newer{"Newer recent file,<br/>or no complete<br/>historical folder?"}
    newer -- no --> done(["Exit: no new data"])
    newer -- yes --> dl["Extract:<br/>download to /tmp"]
    dl --> val{"Headers and<br/>row counts OK?"}
    val -- no --> fail(["Exit 1:<br/>nothing uploaded"])
    val -- yes --> up["Load: upload to a new<br/>timestamped folder"]
    up --> prune["Keep the newest<br/>30 recent folders"]
```

- If the raw zone has no complete historical folder, ingest downloads the
  historical ZIP too. You don't need a separate step for it.

For details, see [Data ingest](3-8-data-ingest.md).

### Seed: first fill of silver

A seed fills an empty `inspections` table from the raw zone. It runs as part
of the load step whenever the table is empty.

- **Run by:** `scripts/deploy.sh` (`pipeline.sh <env> load`) on the first
  deploy. The timer's `run` also seeds if it finds the table empty.

```mermaid
flowchart LR
    load(["load:<br/>table empty"]) --> read["Extract: read historical<br/>+ newest recent CSV<br/>from Blob"]
    read --> xform["Transform in memory:<br/>rename, clean,<br/>split addresses,<br/>de-duplicate"]
    xform --> copy["Load: bulk COPY<br/>into inspections"]
    copy --> log["Add load_log row,<br/>COMMIT"]
```

- The seed is one transaction. If it fails, the table stays empty.

For details, see [Data mapping](3-6-data-mapping.md).

### Refresh: keep silver current

A refresh replaces the recent rows with the newest recent file. The systemd
timer runs it on weekday mornings, right after ingest.

- **Run by:** `dsv-pipeline.timer` (`pipeline.sh <env> run`), Monday to Friday
  at 07:30 Toronto time, plus a random delay of up to 10 minutes. Every
  redeploy also runs it through `scripts/deploy.sh`
  (`pipeline.sh <env> load`), and `scripts/pipeline.sh <env> load --force` reloads the newest file
  by hand.

```mermaid
flowchart LR
    timer(["Timer:<br/>Mon-Fri 07:30"]) --> ingest["Ingest<br/>new files"]
    ingest --> lock["Lock, so only<br/>one load runs"]
    lock --> cur{"Newest blob<br/>already loaded?"}
    cur -- yes --> skip(["Skip"])
    cur -- no --> swap["Delete recent rows,<br/>transform and insert<br/>newest recent CSV"]
    swap --> commit["Add load_log row,<br/>COMMIT"]
    commit --> fresh{"Source data<br/>under 10 days old?"}
    skip --> fresh
    fresh -- yes --> ok(["Exit 0"])
    fresh -- no --> stale(["Exit 1:<br/>stale warning"])
```

- Only the recent window is replaced. Historical rows are loaded once and
  never touched again.
- The swap is atomic: visitors see the old data until `COMMIT`, then the new
  data. No downtime.
- Any failure rolls back, and the site keeps serving the last good load.
- If Toronto Open Data is down, the data only gets older. Nothing breaks.
- Check the last run with `systemctl status dsv-pipeline.service`.

For details, see [Data operations](3-7-data-operations.md).

## Operational events

What happens to each layer when you deploy, redeploy, or restart the app?

Deploys, redeploys, and restarts don't add layers. They're events that run
some of the pipelines, or none. Deploys never contact Toronto Open Data: they
only load from the raw zone.

<!-- prettier-ignore -->
> [!IMPORTANT]
> In a new environment, you must ingest before the first deploy. Run
> `scripts/pipeline.sh <env> ingest`, then `scripts/deploy.sh`.

| Event                          | Bronze (Blob)                 | Silver (Postgres)                                                            |
| ------------------------------ | ----------------------------- | ---------------------------------------------------------------------------- |
| First deploy, empty raw zone   | Untouched                     | Schema created. The load fails, and the deploy fails with an empty database. |
| First deploy, raw zone filled  | Read only                     | Schema created, then **seed**.                                               |
| Redeploy                       | Read only                     | Migrations rerun. Then **refresh** if Blob has a newer file, otherwise skip. |
| Restart or `docker compose up` | Untouched                     | Untouched. The pipeline isn't started by `up`.                               |
| Scheduled run                  | New folder if Toronto changed | **Refresh** or skip, then the staleness check.                               |
| Database volume destroyed      | Untouched                     | Lost. The next deploy is a first deploy, so it seeds from the raw zone.      |

- On every deploy, `deploy.sh` reruns the migrations, then runs the load step.
  Migrations are idempotent.
- If a redeploy's load fails, the deploy prints a warning and the site keeps
  serving the data it already has.
- If the timer fires during a deploy, the load lock makes one load wait for the
  other.

For details, see [Data operations](3-7-data-operations.md).

## Known limits

These limits follow from the design. They matter most while you're changing
the pipeline in stg.

- **Transform changes don't reach historical rows.** A refresh only replaces
  the recent window. If you change the transform, rows before November 2023
  keep the old logic. To reprocess everything, destroy the database volume and
  redeploy, so the next deploy seeds from the raw zone.
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


## Old

