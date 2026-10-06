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
| `dsv-init-analytics` | `curlimages/curl`                    | `backend`           | One-shot: lets anonymous viewers see the dashboard.         |
| `dsv-init-db`        | `ghcr.io/im-kenough/dsv-init-db`     | `backend`           | One-shot: loads `./data` into Postgres with `refresh.py`.   |
| `dsv-data`           | `ghcr.io/im-kenough/dsv-init-db`     | `egress`            | On demand: `data.py fetch` and `sync`. Profile `data`.      |

The `backend` network is internal, so nothing on it reaches the internet or
the instance metadata service. `dsv-data` is the only service on `egress`,
and it has no database credentials. A plain `docker compose up` never starts
it; only `scripts/data.sh` runs it.

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

The data flows one way, from Toronto Open Data to Postgres, through two
containers that share one image but have different network access.

```
 Toronto Open Data
        │  (egress network)
        ▼
 dsv-data  ◄── storage-scoped token file, minted on the host
   fetch → validate → upload changed blobs → manifest.json last
   sync  → mirror blobs to ./data, verify MD5
        │                            ▲
        ▼                            │ service endpoint; firewall allows
 stdsv<env>01 / dinesafe ────────────┘ the VM subnet and HOME_IP
        │
 ./data (read-only mount) ──► dsv-init-db (backend only) ──► dsv-db
```

1.  **Schedule.** `dsv-data.timer` runs `scripts/data.sh <env> --load` at
    07:30 Toronto time on business days. `scripts/deploy.sh` also runs
    `data.sh` before it starts the stack.
2.  **Token.** `data.sh` asks the instance metadata service for a token for
    `https://storage.azure.com/` only, and mounts it into `dsv-data` as a
    mode-600 file. The token never appears in an argument or environment
    variable.
3.  **Fetch.** `data.py fetch` downloads `Dinesafe.csv`, and the historical
    ZIP when the container has no historical files or you pass
    `--historical`. Every file must have the expected columns, decode as
    UTF-8 or cp1252, and have more than a minimum number of rows before
    anything is uploaded. Only files whose MD5 changed are uploaded, and
    `manifest.json` is uploaded last. Each manifest entry records the blob
    version ID it describes.
4.  **Sync.** `data.py sync` downloads the exact blob version of each file
    in the manifest whose MD5 differs from the local copy, checks the MD5, and only then replaces the
    file in `./data`. It removes CSVs that aren't in the manifest.
5.  **Load.** `dsv-init-db` runs `refresh.py`. If the table is empty, it
    seeds the historical and recent files. Otherwise it replaces every row
    on or after the earliest date in the recent CSV, in one transaction.

If Toronto Open Data is down or a file fails validation, `fetch` uploads
nothing, `data.sh` exits 3, and the sync and load run on the last good data
in Blob Storage. For column mapping and the seed and refresh logic, see
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

Local runs use the same data as stg. Your account syncs it from the stg
container with Reader access, from your home IP address:

```bash
az login                      # as dsv-ops01
scripts/data.sh local         # syncs into ./data
docker compose up -d --build
```

If `data.sh local` fails with HTTP 403, your home IP address probably
changed. See
[Troubleshoot: your home IP address changed](../how-to/azure-vm/troubleshoot-home-ip-change.md).

## Where to read next

These documents cover the delivery pipeline and operations in more detail.

- [CI and CD](../explanation/azure-vm/ci-cd.md): how images are built and
  deployed.
- [Deploy DineSafeViz to stg](../how-to/azure-vm/deploy-stg.md): the stg
  deploy, step by step.
- [Data mapping](data-mapping.md): the database schema and how CSV columns
  map to it.
