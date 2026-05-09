# Architecture

The runtime stack uses four Docker Compose services on a shared network:

- **`dsv-db`** — `postgres:17` (latest LTS). On first start, an init
  script creates the table and loads the CSV via `COPY`. Data persists in a
  named volume (`pgdata`).
- **`dsv-app`** — `python:3.12-slim` (latest LTS). Runs the Flask app on
  port 5000. Connects to `dsv-db:5432`. Depends on the database healthcheck
  and on the analytics service being started.
- **`dsv-analytics`** — `grafana/grafana:11.6.0`. Serves the embedded
  analytics dashboard and connects to `dsv-db` as its datasource.
- **`dsv-init-db`** / **`dsv-init-analytics`** — one-shot helper services
  used for data seeding and dashboard permission bootstrap.

## Data Model

One table: `inspections`.
See [data](../data.md)

## CSV Loading

- The init script (`src/db/init.sql`) runs automatically via Postgres's
  `/docker-entrypoint-initdb.d/` mechanism.
- It creates the table, then uses `COPY inspections(...) FROM '/data/Dinesafe.csv' CSV HEADER` to bulk-load the data.
- The CSV file is mounted into the `dsv-db` container at `/data/Dinesafe.csv`
  via a bind mount in `docker-compose.yml`.
- The `_id` column is excluded from the `COPY` column list so it is skipped.

## Web App

- **Route:** Single page at `/`.
- **Query:** `SELECT inspection_date, establishment_name, severity FROM inspections ORDER BY inspection_date DESC`.
- **Display:** HTML table with columns: Date, Establishment, Violations Found.
  - "Violations Found" logic: if `severity` is NULL or the string `'None'`, show **No**. Otherwise show **Yes — {severity}** (e.g. "Yes — M - Minor").
- **Empty state:** If no rows, show "No data available."
- **Styling:** Minimal inline CSS. No JavaScript frameworks.

## File Layout

```text
DineSafeViz/
├── docker-compose.yml
└── src/
    ├── db/
    │   ├── Dinesafe.csv          (existing)
    │   └── init.sql
    ├── grafana/
    │   └── provisioning/
    └── web/
        ├── Dockerfile
        ├── requirements.txt      (flask, psycopg2-binary)
        ├── app.py
        └── templates/
            └── index.html
```

## Configuration

- Postgres credentials passed via environment variables in `docker-compose.yml`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- Flask reads the same credentials from environment to build its connection string.
- Default values: user=`dinesafe`, password=`dinesafe`, db=`dinesafe`.

## Out of Scope

- Authentication, pagination, filtering, search
- Map visualization
- CI/CD
- Production hardening (gunicorn, TLS, etc.)
