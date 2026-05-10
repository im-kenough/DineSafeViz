# Troubleshooting

## Dashboard does not load in Firefox or Chrome

If `/dashboard` renders the page shell but the embedded Grafana view stays
blank, the browser is usually blocking the iframe. Firefox can show a message
such as "localhost:5000 will not allow Firefox to display the page if another
site has embedded it." Chrome commonly shows a refused-to-connect message in
the frame.

Grafana sends `X-Frame-Options: deny` unless embedding is enabled. This project
renders the analytics dashboard inside an iframe on `/dashboard`, so Grafana
must allow embedding.

### Fix

Set `GF_SECURITY_ALLOW_EMBEDDING: "true"` in the `dsv-analytics` service in
`docker-compose.yml`, then recreate the containers so Grafana picks up the new
setting.

```bash
docker compose up -d --build
```

After the containers restart, open `http://localhost:5000/dashboard` again in a
browser tab.


## Dashboard doesn't load in firefox

I have ublock origin and all kinds of ad blockers turn on firefox, it it doesn't load data from postgres, but the dashboard shows up.

firefox normal mode: doesn't load
firefox private mode: loads
chrome normal mode: loads
chrome incognito mode: loads



----



### Services fail to start

Check the logs for each service to identify the issue:

```bash
docker compose logs dsv-db
docker compose logs dsv-app
docker compose logs dsv-analytics
```

Common issues:
- **Port conflicts:** If port 5000 or 3000 is already in use, stop the conflicting service or edit `docker-compose.yml` to use different ports.
- **Insufficient disk space:** Ensure your system has at least 5 GB of free disk space.
- **Database initialization timeout:** If the database takes longer than expected to initialize, check the `dsv-init-db` logs.

### Database won't initialize

If the PostgreSQL database fails to load the CSV data:

```bash
docker compose down -v
docker compose up -d
```

This command removes the existing database volume and restarts from scratch. The `-v` flag removes named volumes.

### Can't connect to the database

Verify the database is healthy:

```bash
docker compose ps dsv-db
```

The `dsv-db` service should show "Up (healthy)". If it shows "(unhealthy)" or "Exited," check the logs:

```bash
docker compose logs dsv-db
```

### Analytics dashboard not loading

The Grafana dashboard may take 30 seconds to fully initialize. Wait a moment and refresh your browser. If it still doesn't load, check:

```bash
docker compose logs dsv-analytics
docker compose logs dsv-init-analytics
```

### Port already in use

If you see an error like "Bind for 0.0.0.0:5000 failed," another process is using that port. You can either:

1. Stop the conflicting process
2. Change the port in `docker-compose.yml`:

```bash
nano docker-compose.yml
```

Find the `ports` section for the `dsv-app` service and change `5000:5000` to `8000:5000` (or another available port).

Then restart:

```bash
docker compose up -d
```
