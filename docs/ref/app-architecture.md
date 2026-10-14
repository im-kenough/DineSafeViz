# App architecture

This reference explains how DineSafeViz works: which containers run, how a
visitor's request reaches the database, how the inspection data gets from
Toronto Open Data into Postgres, and who can access what. It describes the
Azure VM deployment and local development.

## Overview

DineSafeViz shows the City of Toronto's DineSafe restaurant inspection
results. A Flask app serves a map and an inspections browser, and Grafana
serves analytics dashboards, both reading the same Postgres database.

## Services

Every component runs as a Docker Compose service. `docker-compose.yml`
defines the local stack, and `docker-compose.vm.yml` adds the VM settings:
published images, networks, hardening, and memory limits.

| Service              | Image                                | Networks (VM)       | Role                                                        |
| -------------------- | ------------------------------------ | ------------------- | ----------------------------------------------------------- |
| `dsv-tunnel`         | `cloudflare/cloudflared`             | `edge`              | Outbound tunnel to Cloudflare. VM only.                     |
| `dsv-nginx`          | `nginx`                              | `edge`, `backend`   | Reverse proxy for the app and `/analytics/`.                |
| `dsv-app`            | `ghcr.io/im-kenough/dsv-app`         | `backend`           | Flask app. Read-only database role.                         |
| `dsv-db`             | `postgres`                           | `backend`           | Postgres with the `inspections` table.                      |
| `dsv-analytics`      | `grafana/grafana`                    | `backend`           | Dashboards. Read-only database role.                        |
| `dsv-pipeline`       | `ghcr.io/im-kenough/dsv-init-db`     | `egress`, `backend` | On demand: `ingest`, `load`, or `run`. Profile `pipeline`.  |

The `backend` network is internal, so nothing on it reaches the internet or
the instance metadata service. `dsv-pipeline` is the only service on
`egress` and the only one on two networks. Its profile keeps
`docker compose up` from starting it; only `scripts/pipeline.sh` runs it.

## Request path

Visitors never connect to the VM directly. No port is published, and the
tunnel only makes outbound connections.

```
browser → Cloudflare edge → dsv-tunnel → dsv-nginx → dsv-app ──────┐
                                                   → dsv-analytics ─┴→ dsv-db
```

`dsv-app` and `dsv-analytics` connect as the read-only `dinesafe_app` role.
For the admin path over SSH and the network rules, see
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
 │         newest recent/ folder? → download → validate →     │
 │         upload dinesafe/recent/<timestamp>/Dinesafe.csv    │
 │                                                            │
 │ load:   newest recent/ path already in load_log? → skip    │
 │         else download blob → Python transform →            │
 │         DELETE window + COPY into inspections +            │
 │         insert load_log row (1 transaction)                │
 └────────────────────────────────────────────────────────────┘
```

1.  **Schedule.** `dsv-pipeline.timer` runs `scripts/pipeline.sh <env> run`
    at 07:30 Toronto time on business days. `scripts/deploy.sh` runs only
    `load`.
2.  **Token.** `pipeline.sh` asks the instance metadata service for a token
    for `https://storage.azure.com/` only, and mounts it into `dsv-pipeline`
    as a mode-600 file. The token never appears in an argument or
    environment variable.
3.  **Ingest.** Downloads and validates the files from Toronto Open Data,
    then uploads them to new timestamped folders. See
    [Blob layout](../explanation/data-landing-zone.md#blob-layout).
4.  **Load.** Seeds an empty table, or refreshes the recent window, in one
    transaction with a `load_log` row. See
    [The ETL logic](../explanation/data-landing-zone.md#the-etl-logic) and
    [The `load_log` table](../explanation/data-landing-zone.md#the-load_log-table).

A failed ingest leaves the database on its last good load. Deploys never
ingest, so Toronto Open Data can't break a deploy. For column mapping, see
[Data mapping](data-mapping.md).

## Identities and access

No human account holds a standing data role in prod, and every data role is
scoped to a single vault or container.

| Principal                  | Access                                                                   |
| -------------------------- | ------------------------------------------------------------------------ |
| `id-dsv-<env>01-vm`        | Key Vault Secrets User on `kv-dsv-<env>01`; Storage Blob Data Contributor on the `dinesafe` container. |
| `sg-dsv-stg01-operators`   | Key Vault Secrets Officer on `kv-dsv-stg01`; Storage Blob Data Reader on the stg `dinesafe` container. |
| `sg-dsv-prod01-operators`  | Reader on `rg-dsv-prod01`; no data role on prod storage.                  |

The network controls behind these roles:

- **Storage firewall:** default deny. It allows the VM subnet through the
  `Microsoft.Storage` service endpoint, and your home IP address. Shared
  key access is off, so every request needs a Microsoft Entra token.
- **Key Vault firewall:** default deny, with the same subnet and home IP
  rules.
- **Metadata block:** `dsv-imds-block.service` drops container traffic to
  `169.254.169.254` and to the WireServer agent ports on `168.63.129.16`,
  so only host scripts get tokens.
  Each deploy checks that the block holds.
- **Blob versioning and soft delete:** a bad write by the VM identity can be
  rolled back, and its data role can't turn these settings off.

For the full list of accounts and roles, see
[Identity and access management](iam.md).

## Local development

Local runs, the dev environment, use the same data as stg. Your account
loads it from the stg container with Reader access, from your home IP
address. Dev settings and throwaway passwords live in `deploy/dev.env`, like
`deploy/stg.env` and `deploy/prod.env` on the VMs:

```bash
cp deploy/dev.env-example deploy/dev.env   # once
az login                                   # as dsv-ops01
scripts/deploy.sh dev                      # .env, build, start, load
```

For the full steps, see [Deploy DineSafeViz locally](../how-to/deploy-locally.md).

## Where to read next

These documents cover the delivery pipeline and operations in more detail.

- [CI and CD](../explanation/azure-vm/ci-cd.md): how images are built and
  deployed.
- [Deploy DineSafeViz to stg](../how-to/azure-vm/deploy-stg.md): the stg
  deploy, step by step.
- [Data mapping](data-mapping.md): the database schema and how CSV columns
  map to it.
