# Deploy DineSafeViz locally

This guide runs the full DineSafeViz stack on your workstation with Docker
Compose: the Flask app, Postgres, Grafana, and nginx, loaded with the same
inspection data as stg. Use it for development and for testing changes
before they reach stg.

The CSVs aren't in the repository. `scripts/data.sh local` copies them from
the stg Azure Blob Storage container into `./data`, and the stack loads them
from there. For how the pieces fit together, see
[App architecture](../ref/app-architecture.md).

## Before you begin

Confirm the following before you start.

- Docker Engine with the Compose plugin, or Docker Desktop, is installed and
  running.
- The Azure CLI is installed, and you can sign in as `dsv-ops01`. Its group,
  `sg-dsv-stg01-operators`, has Storage Blob Data Reader on the stg
  `dinesafe` container.
- You're on your home network. The storage firewall on `stdsvstg01` only
  allows your home IP address.
- The stg storage account has data. If `data.sh` reports that
  `manifest.json` isn't in the container, run the first data load on the
  stg VM, as described in [Deploy to stg](azure-vm/deploy-stg.md).
- You have a clone of the repository, and you run every command below from
  its root.

## 1. Create the environment file

Compose reads its settings from `.env` in the repository root. The file is
gitignored, so it never gets committed.

1.  Copy the template:

    ```bash
    cp .env.example .env
    ```

2.  Make sure `.env` contains these values. Local passwords don't need to be
    strong, because nothing outside your workstation can reach the stack:

    ```bash
    DSV_DB_PORT=5432
    DSV_DB_NAME=dinesafe
    DSV_DB_USER=dinesafe
    DSV_DB_PASSWORD=dinesafe
    DSV_ANALYTICS_ADMIN_USER=admin
    DSV_ANALYTICS_ADMIN_PASSWORD=admin
    ```

<!-- prettier-ignore -->
> [!IMPORTANT]
> `DSV_DB_NAME` must be `dinesafe`. `src/dsv-db/init.sql` grants privileges
> on a database with that name, so any other value stops the database from
> initializing.

`DSV_DB_USER` and `DSV_DB_PASSWORD` are the Postgres superuser that the data
loader uses. The app and Grafana connect as the read-only `dinesafe_app`
role, which `init.sql` creates with a local default password.

## 2. Sync the data

`scripts/data.sh local` gets a storage token from your Azure CLI sign-in,
then runs the `dsv-data` container to copy the CSVs from `stdsvstg01` into
`./data`. The token reaches the container as a temporary file that's
deleted when the script exits.

1.  Sign in as `dsv-ops01`:

    ```bash
    az login
    az account show --query user.name -o tsv
    ```

    The second command prints the `dsv-ops01` account name.

2.  Sync the CSVs:

    ```bash
    ./scripts/data.sh local
    ```

    The first run builds the `dsv-data` image. The output ends with
    `Sync complete:` and a file count.

3.  Optional: check what you have:

    ```bash
    jq '.fetched_at, (.files | length)' data/manifest.json
    ```

    The output shows when the VM last fetched from Toronto Open Data, and 24
    or more files.

## 3. Start the stack

Build the images and start every service in the background. The first start
pulls the Postgres, Grafana, and nginx images, and loads about 500,000
inspection records, so it takes a few minutes.

```bash
docker compose up -d --build
docker compose logs -f dsv-init-db
```

The load is done when the log shows `Seed complete.`. Press `Ctrl+C` to stop
following the log; the stack keeps running.

## 4. Verify the deployment

Check that every service is up, then open the site.

1.  Check the containers:

    ```bash
    docker compose ps -a
    ```

    `dsv-nginx`, `dsv-app`, `dsv-db`, and `dsv-analytics` show `running` or
    `healthy`. `dsv-init-db` and `dsv-init-analytics` show `exited (0)`.

2.  Open these pages in your browser:

    - Home page: <http://localhost:8080>
    - Inspections: <http://localhost:8080/inspections>
    - Analytics: <http://localhost:8080/analytics/>

    The inspections page opens on the current quarter. Use the year and
    quarter controls to browse back to 2001.

3.  Optional: sign in to Grafana as admin at
    <http://localhost:8080/analytics/login>, with the
    `DSV_ANALYTICS_ADMIN_USER` and `DSV_ANALYTICS_ADMIN_PASSWORD` from
    `.env`.

## Get newer data

The stg VM fetches from Toronto Open Data each business-day morning. To pick
up its latest data, sync again and reload. The sync only downloads files that
changed, and the reload replaces the recent inspections in one transaction.

```bash
./scripts/data.sh local --load
```

## Deploy a code change

Rebuild only what you changed. Each command rebuilds the image and
recreates the container:

| You changed                  | Run                                                        |
| ---------------------------- | ---------------------------------------------------------- |
| `src/dsv-app/`               | `docker compose up -d --build dsv-app`, then `docker compose restart dsv-nginx` |
| `src/dsv-db/refresh.py`      | `docker compose up -d --build dsv-init-db`                 |
| `src/dsv-db/data.py`         | `docker compose --profile data build dsv-data`             |
| `src/dsv-nginx/nginx.conf`   | `docker compose restart dsv-nginx`                         |
| `src/dsv-analytics/`         | `docker compose restart dsv-analytics`                     |
| `src/dsv-db/init.sql`        | Reset the stack, as described in [Stop and reset](#stop-and-reset) |

nginx resolves `dsv-app` once, when it starts. A rebuilt app container gets
a new IP address, so restart nginx after you rebuild the app, or the site
returns `502 Bad Gateway`.

## Stop and reset

These commands stop the stack or start it over.

- Stop the stack and keep the database. The next `docker compose up -d`
  reuses it, so it starts in seconds:

  ```bash
  docker compose down
  ```

- Stop the stack and delete the database and Grafana data. The next start
  loads everything again from `./data`:

  ```bash
  docker compose down -v
  ```

`./data` survives both commands. Delete it only if you want to sync from
scratch.

## Troubleshoot

The following table lists common problems and what to do about them.

| Symptom | Fix |
| ------- | --- |
| `data: can't get a storage token. Run az login as dsv-ops01 first.` | Run `az login`. If you're already signed in, run `az account show` and confirm the account is `dsv-ops01`. |
| `data: GET manifest.json: HTTP 403` | Your IP address isn't in the storage firewall, or the role assignment is new. See [Troubleshoot: your home IP address changed](azure-vm/troubleshoot-home-ip-change.md). A new role assignment can take a few minutes to apply. |
| `data: manifest.json isn't in the container` | stg has no data yet. Run the first data load on the stg VM. |
| `./data isn't writable by <user>` | `docker compose up` ran before `data.sh` and Docker created `./data` as root. Run the `sudo chown` command that the message prints, then sync again. |
| `dsv-init-db` exits with `/data/manifest.json is missing` | Run `./scripts/data.sh local`, then `docker compose up -d`. |
| `dsv-db` keeps restarting | `DSV_DB_NAME` isn't `dinesafe`. Fix `.env`, then run `docker compose down -v` and start again. |
| `502 Bad Gateway` on port 8080 | Run `docker compose restart dsv-nginx`. |
| Port 8080 or 3000 is already in use | Stop the other process, or another copy of the stack, with `docker compose down`. |
| The page loads but shows no inspections | The load is still running, or the selected quarter has no data. Wait for `Seed complete.` in `docker compose logs dsv-init-db`. |

## Next steps

- [Deploy DineSafeViz to stg](azure-vm/deploy-stg.md): run your change on the
  stg VM after it merges to `main`.
- [Data mapping](../ref/data-mapping.md): how the CSV columns map to the
  database.
