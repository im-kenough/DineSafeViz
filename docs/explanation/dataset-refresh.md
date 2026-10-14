# Dataset download and refresh: current design and simpler options

This page describes how DineSafeViz downloads the DineSafe datasets from
Toronto Open Data and refreshes them in Postgres, as of October 11, 2026
(branch `az-12`, after PR #252 moved the CSVs to Azure Blob Storage). It then
lists what the design costs to run and maintain, and compares three ways to
make it simpler. The short version: the pipeline is careful and well tested,
but it uses a firewalled, Entra-only storage account, a token-minting script,
and a dedicated container and network to protect a dataset that's already
public. Publishing the validated CSVs as an image in GHCR, which the VMs
already trust, removes most of those parts and keeps the safety properties.

<!-- prettier-ignore -->
> [!NOTE]
> On October 12, 2026, the project chose a different design: keep the
> private Blob raw zone and simplify the pipeline around it. See
> [Data landing zone](data-landing-zone.md). Options B and C below weren't
> adopted, because they make the raw data public or drop Blob Storage.

For the step-by-step data path, see
[App architecture](../ref/app-architecture.md#data-path). For column mapping
and the seed and refresh SQL, see [Data mapping](../ref/data-mapping.md).

## How it works today

The data moves in three hops: Toronto Open Data to a Blob container, the
container to `./data` on the host, and `./data` to Postgres. Two containers
built from one image (`dsv-init-db`) do the work, each with different network
access and credentials.

```
Toronto Open Data (CKAN, 2 hardcoded resource URLs)
   │  data.py fetch            — stg and prod VMs only, egress network
   ▼
stdsv<env>01 / dinesafe        — versioned, soft delete, Entra-only, firewalled
   │  data.py sync             — VMs and dev, egress network
   ▼
./data (manifest.json, Dinesafe.csv, dinesafe-historical/*.csv)
   │  refresh.py               — dsv-init-db, backend network, read-only mount
   ▼
dsv-db (inspections table)
```

### The datasets

Toronto Open Data publishes two DineSafe resources. Both are public under the
City's open data licence.

| Dataset    | Format and size                               | Changes                                   | Code constant        |
| ---------- | --------------------------------------------- | ----------------------------------------- | -------------------- |
| Recent     | One CSV, about 45 MB, about 120,000 rows      | Rows appended about once per business day | `RECENT_CSV_URL`     |
| Historical | ZIP of 23 yearly CSVs (2001 to 2023)          | Never; it's a static file                 | `HISTORICAL_ZIP_URL` |

The local mirror holds 24 CSVs, about 516,000 rows in 123 MB.

### What runs, and when

Four triggers start some or all of the pipeline. Every trigger goes through
`scripts/data.sh`, except a bare `docker compose up`, which reloads whatever
is already in `./data`.

| Trigger                                   | Where   | Fetch | Sync | Load                              |
| ----------------------------------------- | ------- | ----- | ---- | --------------------------------- |
| `dsv-data.timer`, Monday to Friday 07:30 Toronto time (`scripts/data.sh <env> --load`) | stg, prod | Yes   | Yes  | Yes                               |
| `scripts/deploy.sh stg main` or `prod vX.Y.Z` | stg, prod | Yes   | Yes  | Yes, through `compose up`         |
| `scripts/deploy.sh dev`                   | dev     | No    | From stg | Yes, through `compose up`     |
| `scripts/data.sh dev --load`              | dev     | No    | From stg | Yes                           |
| `docker compose up` (any)                 | any     | No    | No   | Yes, `dsv-init-db` runs every time |

### Step by step

Each step adds a safety property. Together they make sure a bad or partial
download never reaches Postgres.

1.  **Token.** `scripts/data.sh` reads `DSV_STORAGE_ACCOUNT` from
    `deploy/<env>.env`. On a VM it asks IMDS for a token scoped to
    `https://storage.azure.com/` as the VM's managed identity. On dev it asks
    `az account get-access-token`, as `dsv-ops01`. It writes the token to a
    mode-600 temporary file and mounts it into the container. The token never
    appears in an argument or environment variable.
2.  **Fetch** (VMs only). `data.py fetch` reads the remote `manifest.json`,
    downloads the recent CSV, and downloads the historical ZIP only when the
    manifest has no historical files or you pass `--historical`. Every file
    must decode as UTF-8 or cp1252, have the expected columns, and have more
    than a minimum row count (50,000 recent, 1,000 per historical year). If
    any check fails, nothing is uploaded. Files whose MD5 matches the current
    blob are skipped. The manifest is uploaded last, and each entry pins the
    blob version ID it describes.
3.  **Fallback.** If the fetch fails, `data.sh` keeps going with the last good
    data in Blob Storage and exits with status `3`. `deploy.sh` treats `3` as
    a warning. The systemd unit shows `failed`, on purpose.
4.  **Sync.** `data.py sync` downloads each manifest file whose local MD5
    differs, at its pinned version, to a `.part` file. It checks the MD5,
    renames the file into place, deletes CSVs that aren't in the manifest,
    and writes the local `manifest.json` last.
5.  **Load.** `dsv-init-db` runs `refresh.py` with `./data` mounted read-only.
    It exits unless `manifest.json` is present. If the `inspections` table is
    empty, it seeds the historical files (rows before the recent file's
    earliest date) and then the recent file. Otherwise it deletes every row
    on or after the recent file's earliest date and inserts the recent file,
    in one transaction.

### Environments

Each environment has a different relationship to the data. stg and prod each
fetch independently into their own storage account. Dev reads stg's.

| Environment | Producer of its Blob data | Reads from     | Credentials needed on the host                  |
| ----------- | ------------------------- | -------------- | ----------------------------------------------- |
| prod        | prod VM timer and deploys | `stdsvprod01`  | Managed identity, Blob Data Contributor         |
| stg         | stg VM timer and deploys  | `stdsvstg01`   | Managed identity, Blob Data Contributor         |
| dev         | none                      | `stdsvstg01`   | `az login` as `dsv-ops01`, Blob Data Reader, home IP on the storage firewall |

### Supporting infrastructure

The pipeline depends on these pieces outside the Python code:

- **Compose:** the `dsv-data` service (profile `data`), the `egress`
  network, and the `./data` bind mounts on `dsv-data` and `dsv-init-db`.
- **systemd:** `dsv-data.service` and `dsv-data.timer`, installed by hand
  with `sed` placeholders, and `dsv-imds-block.service`, which stops
  containers from getting tokens.
- **Azure, per environment** (`infra/az/setup-az-vms.sh`): the
  `Microsoft.Storage` resource provider registration, a storage account with
  shared keys off and a default-deny firewall, the subnet service endpoint, a
  home IP rule, blob versioning and soft delete, a lifecycle rule that deletes
  versions after 90 days, the container, and two role assignments.
- **Docs:** the data steps in the VM setup and deploy guides, the storage
  part of the home IP troubleshooting guide, and the storage rows in the IAM
  reference.

About 800 lines of code and tests cover the fetch, sync, and wrapper
(`data.sh`, `data.py`, and their tests), separate from the 377-line loader.

## What the design costs

The pipeline works, and its safeguards are real. The costs are in how many
parts you have to understand, keep running, and debug.

- **It protects a public dataset like a secret.** Shared keys off, a default
  deny firewall, Entra tokens, and the IMDS block protect who can *read* the
  storage account. The data is public, so only *integrity* (who can write)
  and *availability* (a last good copy) matter.
- **Two independent producers.** stg and prod each download from Toronto on
  their own schedule. If one fetch fails and the other succeeds, the
  environments serve different data. Dev matches stg only.
- **Dev needs Azure access to get public data.** A new workstation needs
  `az login`, membership in `sg-dsv-stg01-operators`, and a home IP on the
  stg storage firewall. When your IP changes, local deploys fail with HTTP
  `403`.
- **Failures are easy to miss.** The only signal for a failed fetch is a
  `failed` systemd unit on a VM you might not log in to for days. Exit code
  `3` keeps the site up, which is good, but also keeps the failure quiet.
- **Hardcoded download URLs.** Both URLs embed CKAN resource IDs. The recent
  resource ID already changed once, from `eda39233-…` (in the archived docs)
  to `af0f5b8a-…`, when Toronto Public Health changed the schema around June
  2026.
- **Daily work that rarely changes much.** Every business day the VM
  downloads the full 45 MB recent CSV, uploads it as a new blob version, syncs
  it back down, and deletes and reinserts about 120,000 rows on a 1 GiB VM.
  `dsv-init-db` also reloads on every `docker compose up`, including every
  deploy. The lifecycle rule keeps about 60 recent-file versions, a few GB
  per account.
- **Static data on the daily code path.** The historical ZIP never changes,
  but the ZIP handling, the `--historical` flag, and the carry-over logic all
  live in the daily `fetch`.

## Options

The options below go from smallest change to largest. Each keeps the four
safety properties that matter: validate before publishing, keep a last good
copy, pin the exact files you load, and load in one transaction.

### Option A: keep Blob Storage, trim the edges

This option keeps the architecture and fixes the costs that don't depend on
it. Pick it if the Azure storage design is part of what you want the
portfolio to show.

- **Resolve URLs from the CKAN API.** Call
  `https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=dinesafe`
  and pick each resource by name and format, instead of hardcoding resource
  IDs. A changed ID stops being an outage.
- **Alert on failure.** Add `OnFailure=` to `dsv-data.service` to start a
  small unit that posts to a webhook. The spec already proposes a Discord or
  Slack webhook for flow C.
- **Skip unchanged loads.** In `data.sh`, compare `./data/manifest.json`
  before and after the sync, and skip `--load` when they match. Move
  `dsv-init-db` to a Compose profile so `compose up` doesn't reload, and
  have `deploy.sh` run it explicitly only when the table is empty or the
  manifest changed.
- **Make historical a one-time bootstrap.** Move the ZIP handling to a
  separate `data.py bootstrap-historical` command that `deploy.sh` runs only
  when the container has no historical files.

These changes add a little code in places and remove a little in others. The
part count stays about the same, so they make the pipeline sturdier more than
simpler.

### Option B: publish the dataset as a GHCR image (recommended)

This option moves the fetch and validation to a scheduled GitHub Actions
workflow and publishes the validated CSVs as a data-only image in GHCR. The
VMs and dev mount that image read-only into `dsv-init-db`. The storage
accounts, storage tokens, `dsv-data` service, `egress` network, and `sync`
all go away.

```
Toronto Open Data
   │  dataset.yml (GitHub Actions, business-day schedule)
   │  fetch → validate → build FROM scratch → push only if changed
   ▼
ghcr.io/im-kenough/dsv-dataset:2026-10-09 and :latest   (public)
   │  docker pull on the VM timer, deploy, or dev
   ▼
dsv-init-db mounts the image at /data (type: image) → refresh.py → dsv-db
```

How it works:

1.  **Produce.** A new workflow, `.github/workflows/dataset.yml`, runs on a
    business-day schedule and on `workflow_dispatch`. It runs the existing
    download and `validate_csv` code, with `fetch` writing to a directory
    instead of Blob Storage. It builds a `FROM scratch` image with two
    layers: the historical CSVs (cached, so it never changes) and then
    `Dinesafe.csv` with `manifest.json`. If the recent file's MD5 matches the
    current `:latest`, it pushes nothing. Otherwise it pushes a date tag and
    moves `:latest`.
2.  **Consume.** `dsv-init-db` mounts the image instead of `./data`. Compose
    supports image mounts in the long volume syntax:

    ```yaml
    dsv-init-db:
      volumes:
        - type: image
          source: ghcr.io/im-kenough/dsv-dataset:${DSV_DATASET_TAG:-latest}
          target: /data
    ```

3.  **Refresh.** The timer runs
    `docker pull ghcr.io/im-kenough/dsv-dataset:latest` and then
    `docker compose run --rm dsv-init-db`. `deploy.sh` pulls the dataset
    image with the app images.
4.  **Roll back.** Set `DSV_DATASET_TAG` to an earlier date tag in
    `deploy/<env>.env` and rerun the load.

What it keeps and what it changes:

| Property             | Today                                        | With option B                                                    |
| -------------------- | -------------------------------------------- | ---------------------------------------------------------------- |
| Validate first       | `fetch` uploads nothing on failure           | The workflow pushes nothing on failure                            |
| Last good copy       | Current blob versions                        | `:latest` stays on the last good push                             |
| Exact files loaded   | Manifest pins blob version IDs               | The image digest pins every file                                  |
| History              | Blob versions, 90 days                       | Date tags, kept until you delete them                             |
| Who can write        | VM managed identity (RBAC)                   | This repo's workflows (`packages: write`), the same trust as the app images |
| Failure signal       | `failed` systemd unit on the VM              | GitHub emails you about the failed scheduled run                  |
| Environments         | stg and prod fetch independently; dev reads stg | prod, stg, and dev all load the same digest                    |
| Dev setup            | `az login`, operator group, home IP          | None; the package is public                                       |
| VM outbound targets  | Toronto Open Data, Blob Storage, GHCR, Key Vault | GHCR, Key Vault                                               |

What you remove:

- `BlobStore`, `sync`, the manifest version pinning, and their tests in
  `src/dsv-db/data.py` and `src/dsv-db/tests/test_data.py`.
- The token code in `scripts/data.sh`, which shrinks to a pull and a load,
  or goes away and the timer calls those two commands directly.
- The `dsv-data` service and the `egress` network in both Compose files.
- The storage functions in `infra/az/setup-az-vms.sh`,
  `infra/az/storage-lifecycle.json`, the storage role assignments, and the
  storage parts of the IAM, home IP, setup, and deploy docs.

Risks to check before you commit to it:

- **Scheduled workflows pause in quiet repos.** GitHub disables scheduled
  workflows in a public repository after 60 days with no repository
  activity. Add a staleness check on the VM, for example fail the timer when
  `manifest.json`'s `fetched_at` is more than five days old, so a paused
  workflow shows up as a failure.
- **Runner access to Toronto Open Data.** Confirm with a manual
  `workflow_dispatch` run that GitHub-hosted runners can download both files.
  The portal is public, but it might rate-limit or block cloud IP ranges.
- **Docker versions.** Image mounts need a recent Docker Engine, and the
  `image.subpath` option needs Compose 2.35.0 or later. Your workstation runs
  Engine 29.8.2 and Compose v5.6.0; check the VMs, which install Docker from
  Docker's apt repository.
- **A mutable `:latest` tag.** Nothing from the image runs, because it's
  mounted as files and parsed by `refresh.py`. Still, if you want the VM to
  verify where the data came from, add `actions/attest-build-provenance` to
  the workflow and `gh attestation verify` to the timer.
- **Portfolio scope.** This removes the Azure Blob Storage work from the
  project. If showing Entra-only storage, service endpoints, and versioning
  matters for the portfolio, weigh that against the simpler design.

### Option C: drop Blob Storage, fetch on each host

This option removes the middle hop. Each host downloads from Toronto Open
Data, validates into a staging directory, and swaps it into `./data` only
when every file passes. The previous copy stays as `./data.prev` for one-step
rollback. Dev fetches the same way, with no Azure access.

It has the least code of the three, but it gives up the most:

- A rebuilt stg VM, or a new prod VM, can't seed if Toronto Open Data is down
  during its first deploy. Today the last good copy survives in Blob Storage.
- Every environment fetches on its own, so dev, stg, and prod can differ.
- Failures are still only visible on the VM.

### Approaches considered and not recommended

These came up during the review but add parts instead of removing them:

- **One producer, shared container.** Have only one environment fetch and
  grant the others read access. The environments live in separate
  subscriptions, so this needs cross-subscription roles and firewall rules,
  and it couples prod to stg.
- **Incremental downloads from the CKAN DataStore API.** The recent dataset
  is a DataStore table with `_id` values in batch order, so you could fetch
  only new rows. Batches can backfill inspections dated back to 2023, which
  the delete and reinsert by date already handles. At 45 MB a day, the
  savings don't justify paging, state tracking, and a second code path.

## Comparison

The table below scores each option against the costs listed earlier.

| Criterion                                   | Today         | A: trim       | B: GHCR image (recommended) | C: per-host fetch |
| ------------------------------------------- | ------------- | ------------- | --------------------------- | ----------------- |
| Moving parts                                | Many          | About the same | Fewest that keep a shared last good copy | Fewest |
| Dev needs Azure access                      | Yes           | Yes           | No                          | No                |
| New VM seeds while Toronto is down          | Yes           | Yes           | Yes                         | No                |
| All environments load the same data         | No            | No            | Yes                         | No                |
| You hear about a failed fetch               | Only on the VM | Yes (webhook) | Yes (GitHub email)          | Only on the VM    |
| Survives a CKAN resource ID change          | No            | Yes           | Yes, with the API lookup from A | Yes, with the API lookup from A |
| Azure storage shown in the portfolio        | Yes           | Yes           | No                          | No                |
| Effort                                      | —             | Small         | Medium                      | Small to medium   |

## Recommendation

Adopt option B, and carry over the CKAN API lookup from option A, because it
helps every option. It's the only option that makes the pipeline simpler and
also fixes the environment drift and the failure visibility. Do it in this
order, so each step can ship on its own:

1.  Resolve the download URLs through `package_show` (option A's first
    item), in `data.py`, with tests.
2.  Refactor `fetch` to write a validated directory, and add
    `dataset.yml`. Run it by hand with `workflow_dispatch` and confirm the
    runner reaches Toronto Open Data and the image is public.
3.  Switch `dsv-init-db` to the image mount, add `DSV_DATASET_TAG`, update
    `deploy.sh` and the timer, and add the staleness check. Deploy to stg.
4.  After stg has refreshed from GHCR for a week or two, deploy to prod.
5.  Remove `sync`, `BlobStore`, `dsv-data`, the `egress` network, and the
    storage parts of `setup-az-vms.sh` and the docs. Delete the storage
    accounts as an admin change, after you're sure you won't roll back.

If you'd rather keep Blob Storage, do all of option A. The URL lookup and the
failure alert give you the most value for the least work.

## Documentation drift found during the review

These statements in other docs no longer match the code. Fix them whatever
option you choose.

- `docs/ref/data-sources.md` says "`refresh.py` downloads the whole file on
  every run." Since PR #252, `data.py fetch` downloads it, and `refresh.py`
  has no network code.
- `docs/ref/data-mapping.md` names the database image `postgres:17.10`.
  `docker-compose.yml` runs `postgres:18.6`.
- `docs/ref/spec.md` describes flow C as a "nightly ETL refresh" and the
  dataset as "~100k rows." The timer runs on business-day mornings, and the
  table holds about 516,000 rows.
- `docs/ref/iam.md` lists the storage role assignments as `Planned`, but
  `setup-az-vms.sh` creates them, and dev syncs from `stdsvstg01` today.

## Next steps

Choose an option, and then plan the work with these documents:

- [App architecture](../ref/app-architecture.md): the current data path and
  identities.
- [CI and CD](azure-vm/ci-cd.md): how the images workflow builds and
  publishes to GHCR, which option B extends.
- [Schedule the data refresh](../how-to/azure-vm/vm-first-time-setup.md#7-schedule-the-data-refresh):
  the timer setup that options A and B change.
