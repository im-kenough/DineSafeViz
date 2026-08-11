# Troubleshooting

## Dashboard does not load in Firefox or Chrome

If `/dashboard` renders the page shell but the embedded Grafana view stays
blank, the browser is usually blocking the iframe. Firefox can show a message
such as "localhost:8080 will not allow Firefox to display the page if another
site has embedded it." Chrome commonly shows a refused-to-connect message in
the frame.

Grafana sends `X-Frame-Options: deny` unless embedding is enabled. This project
renders the analytics dashboard inside an iframe on `/dashboard`, so Grafana
must allow embedding.

### Fix

Set `GF_SECURITY_ALLOW_EMBEDDING: "true"` in the `dsv-analytics` service in
`docker-compose.yml`. Then recreate the containers so that Grafana picks up the
new setting.

```bash
docker compose up -d --build
```

After the containers restart, open `http://localhost:8080/dashboard` again in a
browser tab.

### Dashboard shell loads but shows no data

An ad blocker or content blocker can block the requests that load data from
PostgreSQL, even though the dashboard shell renders. Observed behavior with
uBlock Origin and other blockers enabled:

- Firefox normal mode: does not load the data
- Firefox private mode: loads
- Chrome normal mode: loads
- Chrome incognito mode: loads

If the dashboard shell renders but no data appears, disable your ad blocker for
the site, or open the page in a private or incognito window.

## Services fail to start

Check the logs for each service to identify the issue.

```bash
docker compose logs dsv-db
docker compose logs dsv-app
docker compose logs dsv-analytics
```

Common issues:

- **Port conflicts:** If port 8080 or 3000 is already in use, stop the
  conflicting service or edit `docker-compose.yml` to use different ports.
- **Insufficient disk space:** Make sure that your system has at least 5 GB of
  free disk space.
- **Database initialization timeout:** If the database takes longer than
  expected to initialize, check the `dsv-init-db` logs.

## Database does not initialize

If the PostgreSQL database fails to load the CSV data, run the following
commands.

```bash
docker compose down -v
docker compose up -d
```

This command removes the existing database volume and restarts from scratch.
The `-v` flag removes named volumes.

## Cannot connect to the database

Verify that the database is running.

```bash
docker compose ps dsv-db
```

The `dsv-db` service should show "Up (healthy)". If it shows "(unhealthy)" or
"Exited", check the logs.

```bash
docker compose logs dsv-db
```

## Analytics dashboard does not load

The Grafana dashboard might take 30 seconds to initialize. Wait a moment, and
then refresh your browser. If it still does not load, check the logs.

```bash
docker compose logs dsv-analytics
docker compose logs dsv-init-analytics
```

## Port already in use

If you see an error such as "Bind for 0.0.0.0:8080 failed," another process is
using that port. You have two options.

1. Stop the conflicting process.
2. Change the port in `docker-compose.yml`.

```bash
nano docker-compose.yml
```

Find the `ports` section for the `dsv-nginx` service, and then change `8080:80`
to another host port, such as `8081:80`.

Then restart the stack.

```bash
docker compose up -d
```
