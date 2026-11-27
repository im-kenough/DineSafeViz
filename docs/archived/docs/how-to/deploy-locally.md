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

    The script writes `.env` from `deploy/dev.env`, builds, starts, waits for
    health, and checks nginx. It then loads stg's raw zone into your
    database, if your database isn't already current. It ends with
    `deploy: dev is running on http://localhost:8080`. The first run loads
    about 500,000 records and takes a few minutes; later runs take seconds.

4.  Open <http://localhost:8080>, <http://localhost:8080/inspections>, and
    <http://localhost:8080/analytics/>. The Grafana admin login is
    `DSV_ANALYTICS_ADMIN_USER` and `DSV_ANALYTICS_ADMIN_PASSWORD` from
    `deploy/dev.env`.

Grafana runs the upstream `grafana/grafana` image, pinned by digest, and uses
the PostgreSQL plugin bundled in it. It doesn't download plugins from
grafana.com. For why, see
[Grafana: the bundled PostgreSQL plugin](../explanation/grafana-postgres-plugin.md).

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
| Load stg's newest data, if it's newer than yours | `./scripts/pipeline.sh dev load` |
| Reload stg's newest data | `./scripts/pipeline.sh dev load --force` |
| Rebuild one service | `docker compose up -d --build dsv-app` |
| Stop, keep the database | `docker compose down` |
| Stop and wipe the database and Grafana | `docker compose down -v` |

After `down -v`, the next deploy or `./scripts/pipeline.sh dev load` seeds the
database again from stg's raw zone. Restarting or rebuilding the stack never
changes the data.
Changes to `src/dsv-db/init.sql` need `down -v`.

## Troubleshoot

| Symptom | Fix |
| ------- | --- |
| `deploy/dev.env is missing` | `cp deploy/dev.env-example deploy/dev.env` |
| `... must contain only letters, digits` or `... is empty` | Fix the named password in `deploy/dev.env`. |
| `can't get a storage token` | `az login` as `dsv-ops01`. |
| `GET https://stdsvstg01... HTTP 403` | Your IP changed or the role is new. See [Troubleshoot: your home IP address changed](azure-vm/troubleshoot-home-ip-change.md). |
| `recent/ is empty` | stg has no data yet. Run `./scripts/pipeline.sh stg ingest` on the stg VM. |
| Dashboards are empty, and the PostgreSQL data source is missing in Grafana | `docker-compose.yml` points `dsv-analytics` at an image without the bundled plugin, such as a `-slim` one. Use the full image. |
| `docker compose logs dsv-analytics` shows `Skipping loading of plugin as it's a duplicate` for `grafana-postgresql-datasource` | Your Grafana volume holds a plugin that an earlier Grafana 13.2 downloaded, and Grafana uses it instead of the bundled one. Run the cleanup after this table once. |
| `password authentication failed` in logs | `docker compose down -v`, then deploy again. |
| Port 8080 or 3000 in use | Stop the other process or stack. |
| You still have a `./data` folder | It's no longer used. Delete it: `rm -rf data` |

To remove the downloaded plugins from the Grafana volume, run the following
commands. They keep Grafana's database, `grafana.db`, so dashboards and users
survive.

```bash
docker compose run --rm --no-deps --entrypoint sh dsv-analytics \
  -c 'rm -rf /var/lib/grafana/plugins/*'
docker compose restart dsv-analytics
```

## Next steps

- [Deploy DineSafeViz to stg](azure-vm/deploy-stg.md)
- [App architecture](../ref/app-architecture.md)
