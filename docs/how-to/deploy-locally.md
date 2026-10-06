# Deploy DineSafeViz locally

This guide runs the full stack (app, Postgres, Grafana, nginx) on your
workstation, the dev environment, with the same CSVs as stg. Dev works like
stg and prod: settings live in `deploy/dev.env`, and `scripts/deploy.sh`
deploys. Dev has no Key Vault, so its throwaway passwords live in
`deploy/dev.env` too.

## Before you begin

You need the following:

- Docker with the Compose plugin.
- The Azure CLI, signed in as `dsv-ops01` (Storage Blob Data Reader on
  `stdsvstg01/dinesafe`).
- Your home network. The `stdsvstg01` firewall only allows your home IP.

## Deploy

Run these commands from the repository root.

1.  Create your settings file. It's gitignored. The default passwords are
    fine; if you change them, use only letters, digits, and `. _ ~ -`.

    ```bash
    cp deploy/dev.env-example deploy/dev.env
    ```

2.  Sign in to Azure:

    ```bash
    az login
    az account show --query user.name -o tsv    # prints dsv-ops01
    ```

3.  Deploy:

    ```bash
    ./scripts/deploy.sh dev
    ```

    The script writes `.env` from `deploy/dev.env`, syncs the CSVs into
    `./data`, builds, starts, waits for health, and checks nginx. It ends with
    `deploy: dev is running on http://localhost:8080`. The first run loads
    about 500,000 records and takes a few minutes; later runs take seconds.

4.  Open <http://localhost:8080>, <http://localhost:8080/inspections>, and
    <http://localhost:8080/analytics/>. The Grafana admin login is
    `DSV_ANALYTICS_ADMIN_USER` and `DSV_ANALYTICS_ADMIN_PASSWORD` from
    `deploy/dev.env`.

<!-- prettier-ignore -->
> [!IMPORTANT]
> Edit `deploy/dev.env`, never `.env`: every deploy rewrites `.env`.
> `DSV_DB_NAME` must stay `dinesafe`. Postgres reads its passwords only when
> its volume is new, so after changing one run `docker compose down -v`, then
> deploy again.

## Day-to-day commands

| Task | Command |
| ---- | ------- |
| Redeploy after a code change | `./scripts/deploy.sh dev` |
| Pull stg's latest CSVs and reload | `./scripts/data.sh dev --load` |
| Rebuild one service | `docker compose up -d --build dsv-app` |
| Stop, keep the database | `docker compose down` |
| Stop and wipe the database and Grafana | `docker compose down -v` |

`./data` survives `down -v`, so the next deploy reloads without downloading.
Changes to `src/dsv-db/init.sql` need `down -v`.

## Troubleshoot

| Symptom | Fix |
| ------- | --- |
| `deploy/dev.env is missing` | `cp deploy/dev.env-example deploy/dev.env` |
| `... must contain only letters, digits` or `... is empty` | Fix the named password in `deploy/dev.env`. |
| `can't get a storage token` | `az login` as `dsv-ops01`. |
| `GET manifest.json: HTTP 403` | Your IP changed or the role is new. See [Troubleshoot: your home IP address changed](azure-vm/troubleshoot-home-ip-change.md). |
| `manifest.json isn't in the container` | stg has no data yet. See [Deploy to stg](azure-vm/deploy-stg.md). |
| `./data isn't writable` | Run the `sudo chown` command the message prints. |
| `password authentication failed` in logs | `docker compose down -v`, then deploy again. |
| Port 8080 or 3000 in use | Stop the other process or stack. |

## Next steps

- [Deploy DineSafeViz to stg](azure-vm/deploy-stg.md)
- [App architecture](../ref/app-architecture.md)
