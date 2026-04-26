# DineSafeViz Proof of Concept — Design Spec

## Goal

Load Toronto DineSafe inspection data from CSV into a Postgres database and display it via a simple Flask web app. Both services run in Docker Compose.

## Architecture

Two Docker Compose services on a shared network:

- **db** — `postgres:17` (latest LTS). On first start, an init script creates the table and loads the CSV via `COPY`. Data persists in a named volume (`pgdata`).
- **web** — `python:3.12-slim` (latest LTS). Runs a Flask app on port 5000. Connects to `db:5432`. Depends on db being healthy (`pg_isready` healthcheck).

## Data Model

One table: `inspections`.

```sql
CREATE TABLE inspections (
    id                     SERIAL PRIMARY KEY,
    establishment_id       TEXT,
    inspection_id          TEXT,
    establishment_name     TEXT,
    establishment_type     TEXT,
    establishment_address  TEXT,
    infraction_details     TEXT,
    inspection_observation TEXT,
    inspection_date        DATE,
    severity               TEXT,
    action                 TEXT,
    outcome                TEXT,
    outcome_date           TEXT,
    amount_fined           TEXT,
    latitude               DOUBLE PRECISION,
    longitude              DOUBLE PRECISION,
    unique_id              TEXT
);
```

- The `_id` column from the CSV (Open Data row ID) is skipped; we use our own `SERIAL` primary key.
- No additional indexes for the proof of concept.

## CSV Loading

- The init script (`db/init.sql`) runs automatically via Postgres's `/docker-entrypoint-initdb.d/` mechanism.
- It creates the table, then uses `COPY inspections(...) FROM '/data/Dinesafe.csv' CSV HEADER` to bulk-load the data.
- The CSV file is mounted into the db container at `/data/Dinesafe.csv` via a bind mount in `docker-compose.yml`.
- The `_id` column is excluded from the `COPY` column list so it is skipped.

## Web App

- **Route:** Single page at `/`.
- **Query:** `SELECT inspection_date, establishment_name, severity FROM inspections ORDER BY inspection_date DESC`.
- **Display:** HTML table with columns: Date, Establishment, Violations Found.
  - "Violations Found" logic: if `severity` is NULL or the string `'None'`, show **No**. Otherwise show **Yes — {severity}** (e.g. "Yes — M - Minor").
- **Empty state:** If no rows, show "No data available."
- **Styling:** Minimal inline CSS. No JavaScript frameworks.

## File Layout

```
DineSafeViz/
├── docker-compose.yml
├── db/
│   ├── Dinesafe.csv          (existing)
│   └── init.sql
├── web/
│   ├── Dockerfile
│   ├── requirements.txt      (flask, psycopg2-binary)
│   ├── app.py
│   └── templates/
│       └── index.html
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

## Notes

- `src/tools/create_db.py` exists but is empty and unused by this design.
