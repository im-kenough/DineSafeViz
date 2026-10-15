# Data architecture

This page gives a high-level view of how DineSafe inspection data moves from
Toronto Open Data into Postgres and stays current. Each section links to a
sub-document with the implementation details.

## Infrastructure

The data path has three zones: raw files in Azure Blob Storage, a temporary
transform step, and the Postgres database the site reads. One service,
`dsv-pipeline`, writes data. Everything else only reads.

```mermaid
flowchart LR
    tod["Toronto Open Data<br/>(public internet)"]

    subgraph azure["Azure subscription"]
        kv["Key Vault<br/>DB passwords"]
        mi["VM managed identity<br/>id-dsv-stg01-vm / id-dsv-prod01-vm"]
        blob[("Storage account<br/>stdsvstg01 / stdsvprod01<br/>Blob container: dinesafe<br/>RAW ZONE")]

        subgraph vm["VM (Docker Compose)"]
            timer["systemd timer<br/>weekdays 07:30"]
            pipe["dsv-pipeline<br/>ingest + TRANSFORM"]
            db[("dsv-db<br/>Postgres<br/>SERVING ZONE")]
            app["dsv-app<br/>website"]
            graf["dsv-analytics<br/>Grafana"]
        end
    end

    timer -- starts --> pipe
    mi -. "storage token" .-> pipe
    kv -. ".env passwords" .-> vm
    tod -- "1. download CSV + ZIP" --> pipe
    pipe -- "2. upload raw files" --> blob
    blob -- "3. read raw files" --> pipe
    pipe -- "4. write rows" --> db
    db -- "read only" --> app
    db -- "read only" --> graf
```

| Component       | Pulls                    | Transforms          | Stores                          |
| --------------- | ------------------------ | ------------------- | ------------------------------- |
| `dsv-pipeline`  | Toronto Open Data, Blob  | Yes, in memory      | Nothing. One-shot container.    |
| Blob `dinesafe` | —                        | No                  | Raw files, as downloaded        |
| `dsv-db`        | —                        | No                  | `inspections` and `load_log`    |
| `dsv-app`       | `dsv-db`                 | No                  | A small stats cache, in memory  |
| `dsv-analytics` | `dsv-db`                 | No                  | Nothing                         |

- Same layout in stg and prod. Dev reads stg's storage, read-only.
- Only `dsv-pipeline` can reach the internet. The app and Grafana can't.
- The raw zone is the backup: it can rebuild the database without Toronto.
- `docker compose up` and restarts never change data.

For details, see [App architecture](2-app-architecture.md),
[Data operations](3-7-data-operations.md#access-and-credentials), and
[Data readers](3-9-data-readers.md).

## How raw data is ingested

Ingest copies new files from Toronto Open Data to Blob Storage. It never
touches the database.

```mermaid
flowchart LR
    start(["ingest"]) --> ask["Ask Toronto's catalog<br/>when files last changed"]
    ask --> newer{"Newer recent file,<br/>or no complete<br/>historical folder?"}
    newer -- no --> done(["Exit: no new data"])
    newer -- yes --> dl["Download to /tmp"]
    dl --> val{"Headers and<br/>row counts OK?"}
    val -- no --> fail(["Exit 1:<br/>nothing uploaded"])
    val -- yes --> up["Upload to a new<br/>timestamped folder"]
    up --> prune["Keep the newest<br/>30 recent folders"]
```

- Two source files:
  - **Recent:** `Dinesafe.csv`, November 2023 to today. Updated often.
  - **Historical:** a ZIP of yearly CSVs, 2001 to 2023. Downloaded once.
- Each ingest writes a new folder. Existing files are never overwritten.
- A bad download is rejected before upload, so the raw zone only holds files
  that passed validation.
- Uses the VM's managed identity. No storage keys.

For details, see [Data sources](3-2-data-sources.md) and
[Data ingest](3-8-data-ingest.md).

## How the database is created and populated

Postgres creates the empty schema on first start. The pipeline then fills it
from the raw zone. This first fill is called a *seed*.

```mermaid
flowchart LR
    vol(["Empty dsv-db-data<br/>volume"]) --> init["Postgres runs init.sql<br/>and migrations:<br/>tables, roles, grants"]
    init --> deploy["deploy.sh reruns<br/>migrations"]
    deploy --> load["pipeline load:<br/>table empty, so seed"]
    load --> read["Read historical<br/>+ recent CSVs<br/>from Blob"]
    read --> xform["Transform:<br/>rename, clean,<br/>de-duplicate"]
    xform --> copy["Bulk COPY into<br/>inspections"]
    copy --> log["Add load_log row,<br/>COMMIT"]
```

- Two tables:
  - `inspections`: one row per infraction, about 508,000 rows.
  - `load_log`: one row per successful load.
- Three database roles, each with least access:
  - Superuser: creates the schema only.
  - `dinesafe_migrator`: the pipeline. Read, insert, and delete.
  - `dinesafe_app`: the app and Grafana. Read only.
- The seed is one transaction. If it fails, the table stays empty and the
  deploy fails.
- Every deploy runs the load step. On an existing database it refreshes or
  skips instead of seeding.

For details, see [Database](3-5-database.md) and
[Data mapping](3-6-data-mapping.md).

## How the data is updated

A systemd timer runs the pipeline on weekday mornings. Each run ingests new
files, then replaces the recent rows in the database.

```mermaid
flowchart LR
    timer(["Timer:<br/>Mon-Fri 07:30"]) --> ingest["Ingest<br/>new files"]
    ingest --> lock["Lock, so only<br/>one load runs"]
    lock --> cur{"Newest blob<br/>already loaded?"}
    cur -- yes --> skip(["Skip"])
    cur -- no --> swap["Delete recent rows,<br/>insert newest recent CSV"]
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
