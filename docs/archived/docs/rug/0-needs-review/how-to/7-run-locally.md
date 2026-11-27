# Run DineSafeViz locally with Docker Desktop

This guide shows you how to run the full DineSafeViz stack on your own machine
with Docker Desktop, seeded from the DineSafe CSVs in the stg Azure Blob
Storage container. This is meant for testing and development. For the
production deployment on Proxmox, see the [deploy guide](1-install/6-deploy.md)
instead.

The CSVs aren't in the repository. `scripts/data.sh local` syncs them from
stg into `./data`, so your local stack loads the same data as stg.

## Prerequisites

You need the following before you start.

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and
  running (it includes Docker Compose).
- A local clone of this repository.
- The Azure CLI, signed in as `dsv-ops01`. Its operator group has Storage
  Blob Data Reader on the stg `dinesafe` container.
- Your home network. The storage firewall only allows your home IP address,
  so a sync from anywhere else fails with HTTP 403.

## Step 1: create your environment file

The stack reads configuration from a `.env` file in the repository root. Copy
the example and set the values below.

1. From the repository root, copy the template:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` so it contains these values:

   ```bash
   DSV_DB_PORT=5432
   DSV_DB_USER=dinesafe
   DSV_DB_PASSWORD=dinesafe
   DSV_DB_NAME=dinesafe
   DSV_ANALYTICS_ADMIN_USER=admin
   DSV_ANALYTICS_ADMIN_PASSWORD=admin
   ```

<!-- prettier-ignore -->
> [!IMPORTANT]
> `DSV_DB_NAME` must be `dinesafe`. The database bootstrap script
> (`src/dsv-db/init.sql`) grants privileges on a database named `dinesafe`, so a
> different name makes the database container fail to initialize.

The `DSV_DB_USER` and `DSV_DB_PASSWORD` values are the PostgreSQL superuser that
the seeder uses. The application and Grafana connect with a separate, read-only
role that `init.sql` creates automatically, so you don't set those here.

## Step 2: sync the data

The seeder reads the CSVs from `./data`, which `docker-compose.yml` mounts
read-only at `/data`. Fill it from the stg Blob container:

```bash
az login                      # as dsv-ops01
scripts/data.sh local
```

The output ends with `Sync complete:` and a file count. `./data` is
gitignored. Run the sync again whenever you want newer data; it only
downloads files that changed.

<!-- prettier-ignore -->
> [!NOTE]
> If the sync fails with HTTP 403 (`AuthorizationFailure`), the storage
> firewall doesn't allow your current IP address. See
> [Troubleshoot: your home IP address changed](../../../how-to/azure-vm/troubleshoot-home-ip-change.md).

## Step 3: start the stack

Build the images and start every service in the background. The first run builds
the application image and pulls the PostgreSQL, Grafana, and NGINX images, so it
takes a few minutes.

```bash
docker compose up -d --build
```

The seeder (`dsv-init-db`) runs once and then exits. Watch its progress and wait
for it to finish loading the data:

```bash
docker compose logs -f dsv-init-db
```

The seed is complete when you see `Seed complete.` in the logs. The full dataset
is about 500,000 inspection records spanning 2001 to the present.

## Step 4: open the application

Once the seed finishes, the stack is ready. Open these URLs in your browser.

- Home page: <http://localhost:8080>
- Inspections: <http://localhost:8080/inspections>
- Analytics (Grafana): <http://localhost:8080/analytics/>

The inspections page defaults to the current quarter. Use the year and quarter
navigation to browse historical data back to 2001.

## Stop and reset

Use these commands to stop or reset the stack.

- Stop the stack but keep the database (a later start reuses the existing data,
  so no reseed is needed):

  ```bash
  docker compose down
  ```

- Stop the stack and delete all data (the next start reseeds from scratch):

  ```bash
  docker compose down -v
  ```

<!-- prettier-ignore -->
> [!NOTE]
> The seeder only loads data when the database is empty. After the first seed,
> restarting the stack reuses the existing data. To force a fresh seed, run
> `docker compose down -v` first to remove the database volume.

## How the seed works

The seeder is a small Python script, `src/dsv-db/refresh.py`. It reads only
the files in `./data` and stops with a message if `manifest.json` is
missing. The Azure VMs use the same script and the same files, so local
testing exercises the same loading logic that runs in production. For the
whole data path, see [App architecture](../../../ref/app-architecture.md).

The DineSafe CSV files mix character encodings across years (older files are
UTF-8, newer ones are Windows-1252). The seeder detects and handles both, so
accented establishment names load correctly either way.

## Troubleshooting

Use these checks when the stack doesn't come up as expected.

### The seeder exits with an error

If the logs say `/data/manifest.json is missing`, run `scripts/data.sh local`
first. For other failures, check the seeder logs:

```bash
docker compose logs dsv-init-db
```

A `could not connect` error usually means the database wasn't ready yet. The
seeder waits for the database health check, so retry the start:

```bash
docker compose up -d
```

### The database container keeps restarting

Confirm `DSV_DB_NAME=dinesafe` in your `.env` file. Any other value makes
`init.sql` fail because it grants privileges on a database named `dinesafe`. If
you already started the stack with the wrong name, remove the volume and start
again:

```bash
docker compose down -v
docker compose up -d --build
```

### Port 8080 or 3000 is already in use

Another process (or a second copy of this stack) is using the port. Stop the
other process, or stop any existing stack with `docker compose down`.

### The application page loads but shows no inspections

The seed may still be running, or the selected quarter has no data. Wait for
`Seed complete.` in the seeder logs, then use the year and quarter navigation to
select a period that contains inspections.
