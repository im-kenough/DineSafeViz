# App architecture

This reference explains how DineSafeViz works: which containers run, how a
visitor's request reaches the database, how the inspection data gets from
Toronto Open Data into Postgres, and who can access what. It describes the
Azure VM deployment and local development.

## Overview

DineSafeViz shows the City of Toronto's DineSafe restaurant inspection
results. A Flask app serves the web pages, and Grafana serves an analytics
dashboard. Both read the same Postgres database, and nginx sits in front of
both.

The Flask app (`src/dsv-app/app.py`) serves these routes:

| Route                 | Page                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `/`                   | Home page with the total number of inspections and the years of data.                     |
| `/inspections`        | Inspections for one quarter (`?year=&q=`), grouped by day and establishment.              |
| `/inspections/month`  | One month's inspections as an HTML fragment, loaded when you expand an older month.       |
| `/dashboard`          | The Grafana dashboard in an iframe (`/analytics/d/dinesafe/dinesafe-inspections?kiosk`). |
| `/info`               | What the severities and results mean.                                                      |
| `/healthz`, `/readyz` | Liveness, and readiness, which checks the database connection.                             |

Gunicorn runs the app with one worker and four threads. The home page stats
come from a `SELECT DISTINCT` over the whole table, so the app caches them
in memory for five days. It doesn't cache an empty result, so the page
updates as soon as the first seed commits.

## Services

Every component runs as a Docker Compose service. `docker-compose.yml`
defines the local stack, and `docker-compose.vm.yml` adds the VM settings:
published images, networks, hardening, and memory limits.

| Service         | Image                                 | Networks (VM)       | Memory (VM) | Role                                                       |
| --------------- | ------------------------------------- | ------------------- | ----------- | ---------------------------------------------------------- |
| `dsv-tunnel`    | `cloudflare/cloudflared:2026.10.0`    | `edge`              | 64 MiB      | Outbound tunnel to Cloudflare. VM only.                    |
| `dsv-nginx`     | `nginx:1.31.0-alpine-slim`            | `edge`, `backend`   | 64 MiB      | Reverse proxy for the app and `/analytics/`.               |
| `dsv-app`       | `ghcr.io/im-kenough/dsv-app`          | `backend`           | 192 MiB     | Flask app. Read-only database role.                        |
| `dsv-db`        | `postgres:18.6-alpine3.24`            | `backend`           | 320 MiB     | Postgres with the `inspections` and `load_log` tables.     |
| `dsv-analytics` | `grafana/grafana:13.2.3`              | `backend`           | 320 MiB     | Dashboard. Read-only database role.                        |
| `dsv-pipeline`  | `ghcr.io/im-kenough/dsv-init-db`      | `egress`, `backend` | 768 MiB     | On demand: `ingest`, `load`, or `run`. Profile `pipeline`. |

Locally, Compose builds `dsv-app` and `dsv-pipeline` from `src/dsv-app` and
`src/dsv-db`, and every service shares the default network. On the VMs, the
two app images are pinned to the deployed version's tag. Every service sets
`no-new-privileges` and rotates its logs. Every service except
`dsv-analytics` drops all Linux capabilities and adds back only the ones it
needs. `dsv-tunnel`, `dsv-app`, and `dsv-pipeline` also run with a read-only
root filesystem.

The `backend` network is internal, so nothing on it reaches the internet or
the instance metadata service. `dsv-pipeline` is the only service on
`egress`, and the only one that can reach both the internet and the
database. Its profile keeps `docker compose up` from starting it; only
`scripts/pipeline.sh` runs it.

## Request path

Visitors never connect to the VM directly. No port is published, and the
tunnel only makes outbound connections.

```
browser → Cloudflare edge → dsv-tunnel → dsv-nginx → dsv-app ──────┐
                                                   → dsv-analytics ─┴→ dsv-db
```

nginx sends `/analytics/` to Grafana and everything else to the app. It
re-resolves the container names every 5 seconds, so a recreated container
with a new IP address doesn't cause 502 errors.

`dsv-app` and `dsv-analytics` connect as the read-only `dinesafe_app` role,
which caps every query at 10 seconds. Visitors see Grafana as anonymous
viewers. On the VMs, nginx returns 404 for `/analytics/login`, so Grafana
admins sign in through an SSH tunnel to `172.30.10.30:3000` instead. For the
admin path over SSH and the network rules, see
[Network paths](../explanation/azure-vm/network-paths.md).

## Data path

The data flows one way: from Toronto Open Data, into the Blob raw zone, and
then into Postgres. One one-shot container, `dsv-pipeline`, does both steps.

```
           07:30 timer, deploy, or your command
                        │
                        ▼
 ┌──────────── dsv-pipeline (one-shot container) ────────────┐
 │ ingest: CKAN package_show → last_modified newer than       │
 │         newest recent/ file? → download → validate →      │
 │         upload dinesafe/recent/<timestamp>/Dinesafe.csv →  │
 │         prune recent/ to the newest 30 folders             │
 │                                                            │
 │ load:   empty table? → seed (historical + recent)          │
 │         newest recent/ path already in load_log? → skip    │
 │         else download blob → Python transform →            │
 │         DELETE window + COPY into inspections +            │
 │         insert load_log row (1 transaction)                │
 │                                                            │
 │ run:    ingest, load, then fail if the newest source data  │
 │         is more than 10 days old                           │
 └────────────────────────────────────────────────────────────┘
```

1.  **Schedule.** `dsv-pipeline.timer` runs `scripts/pipeline.sh <env> run`
    at 07:30 Toronto time on weekdays, with up to 10 minutes of random
    delay. A missed run starts when the VM next boots, and a run that takes
    over 30 minutes is stopped.
2.  **Deploy.** `scripts/deploy.sh` applies the database migrations, then
    runs only `load`. If the load fails and the table already has data, the
    deploy warns and keeps serving it. If the table is empty, the deploy
    fails.
3.  **Token.** On the VMs, `pipeline.sh` asks the instance metadata service
    for a token for `https://storage.azure.com/` only. Locally, it gets the
    token from your `az login`. Either way, it mounts the token into
    `dsv-pipeline` as a mode-600 file and deletes it on exit. The token never
    appears in an argument or environment variable.
4.  **Ingest.** Downloads the recent CSV when Toronto Open Data has a newer
    one, and the historical ZIP when the raw zone has no complete copy or
    you pass `--historical`. It checks every file's columns and row count
    before it uploads anything, and doesn't upload a recent file identical
    to the newest one. See
    [Blob layout](../explanation/data-landing-zone.md#blob-layout).
5.  **Load.** Seeds an empty table, or refreshes the recent window, in one
    transaction with a `load_log` row. An advisory lock stops a deploy's
    load and the timer's load from running at the same time. See
    [The ETL logic](../explanation/data-landing-zone.md#the-etl-logic) and
    [The `load_log` table](../explanation/data-landing-zone.md#the-load_log-table).

A failed ingest or load leaves the database on its last good load. Deploys
never ingest, so Toronto Open Data can't break a deploy. For the source
files, see [Data sources](data-sources.md). For column mapping, see
[Data mapping](data-mapping.md).

## Identities and access

No human account holds a standing data role in prod, and every data role is
scoped to a single vault or container. The following table lists the data
roles. For every role, including management roles, see
[Identity and access management](iam.md).

| Principal                 | Data access                                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| `id-dsv-<env>01-vm`       | Key Vault Secrets User on `kv-dsv-<env>01`; Storage Blob Data Contributor on the `dinesafe` container. |
| `sg-dsv-stg01-operators`  | Key Vault Secrets Officer on `kv-dsv-stg01`; Storage Blob Data Reader on the stg `dinesafe` container. |
| `sg-dsv-prod01-operators` | Key Vault Secrets Officer on `kv-dsv-prod01` (planned); no data role on prod storage.                   |

The network controls behind these roles:

- **Storage firewall:** default deny. It allows the VM subnet through the
  `Microsoft.Storage` service endpoint, and your home IP address. Shared
  key access is off, so every request needs a Microsoft Entra token.
- **Key Vault firewall:** default deny, with the same subnet and home IP
  rules.
- **Metadata block:** `dsv-imds-block.service` drops container traffic to
  `169.254.169.254` and to the WireServer agent ports on `168.63.129.16`,
  so only host scripts get tokens. Each deploy checks that the block holds.
- **Blob versioning and soft delete:** a bad write by the VM identity can be
  rolled back, and its data role can't turn these settings off.

## Local development

Local runs, the dev environment, use the same data as stg. Your account
loads it from the stg container with Reader access, from your home IP
address. Dev settings and throwaway passwords live in `deploy/dev.env`, like
`deploy/stg.env` and `deploy/prod.env` on the VMs.

To deploy locally, run these commands from the repository root:

```bash
cp deploy/dev.env-example deploy/dev.env   # once
az login                                   # as dsv-ops01
scripts/deploy.sh dev                      # .env, build, start, migrate, load
```

The site is on http://localhost:8080, and Grafana is also published directly
on http://localhost:3000. Dev can only `load`; it never ingests. For the full
steps, see [Deploy DineSafeViz locally](../how-to/deploy-locally.md).

## Next steps

These documents cover the delivery pipeline and operations in more detail.

- [CI and CD](../explanation/azure-vm/ci-cd.md): how images are built and
  deployed.
- [Deploy DineSafeViz to stg](../how-to/azure-vm/deploy-stg.md): the stg
  deploy, step by step.
- [Data mapping](data-mapping.md): the database schema and how CSV columns
  map to it.
