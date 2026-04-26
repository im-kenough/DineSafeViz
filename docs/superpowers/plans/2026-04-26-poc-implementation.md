# DineSafeViz PoC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load DineSafe CSV into Postgres and display inspections via Flask, all in Docker Compose.

**Architecture:** Two Docker Compose services — `db` (Postgres 17) with an init script that creates a staging table, bulk-loads the CSV, transforms into the final `inspections` table; and `web` (Flask on Python 3.12-slim) that queries and renders a single HTML page.

**Tech Stack:** PostgreSQL 17, Python 3.12, Flask, psycopg2-binary, Docker, Docker Compose

**Spec:** `docs/superpowers/specs/2026-04-26-poc-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `db/init.sql` | CREATE TABLE, staging COPY, transform, cleanup |
| `docker-compose.yml` | Define db + web services, volumes, healthcheck |
| `web/Dockerfile` | Build Flask app image |
| `web/requirements.txt` | Python dependencies |
| `web/app.py` | Flask app — single route, DB query, render |
| `web/templates/index.html` | Jinja2 template — inspection table |

---

### Task 1: Database init script

**Files:**
- Create: `db/init.sql`

**Context:** The CSV (`db/Dinesafe.csv`) has 17 columns. The first column `_id` is an Open Data row ID we don't need. Some fields contain the string `None` instead of actual NULLs. Addresses contain commas inside quoted fields. The file has Windows line endings (`\r\n`) — Postgres COPY CSV handles both issues natively.

The strategy: create a staging table (all TEXT columns matching CSV layout), COPY the CSV into it, then INSERT into the real `inspections` table with type casting and NULL conversion, then drop the staging table.

- [ ] **Step 1: Create `db/init.sql`**

```sql
-- Create the final inspections table
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

-- Staging table: all TEXT, matches CSV column order exactly (17 columns)
CREATE TABLE _csv_staging (
    _id                    TEXT,
    establishment_id       TEXT,
    inspection_id          TEXT,
    establishment_name     TEXT,
    establishment_type     TEXT,
    establishment_address  TEXT,
    infraction_details     TEXT,
    inspection_observation TEXT,
    inspection_date        TEXT,
    severity               TEXT,
    action                 TEXT,
    outcome                TEXT,
    outcome_date           TEXT,
    amount_fined           TEXT,
    latitude               TEXT,
    longitude              TEXT,
    unique_id              TEXT
);

-- Bulk load CSV (HEADER skips the first line, CSV handles quoted commas and CRLF)
COPY _csv_staging FROM '/data/Dinesafe.csv' WITH (FORMAT csv, HEADER true);

-- Transform into final table, converting 'None'/empty strings to actual NULLs
INSERT INTO inspections (
    establishment_id, inspection_id, establishment_name, establishment_type,
    establishment_address, infraction_details, inspection_observation,
    inspection_date, severity, action, outcome, outcome_date, amount_fined,
    latitude, longitude, unique_id
)
SELECT
    NULLIF(establishment_id, 'None'),
    NULLIF(inspection_id, 'None'),
    NULLIF(establishment_name, 'None'),
    NULLIF(establishment_type, 'None'),
    NULLIF(establishment_address, 'None'),
    NULLIF(infraction_details, 'None'),
    NULLIF(inspection_observation, 'None'),
    NULLIF(inspection_date, 'None')::DATE,
    NULLIF(severity, 'None'),
    NULLIF(action, 'None'),
    NULLIF(outcome, 'None'),
    NULLIF(outcome_date, 'None'),
    NULLIF(NULLIF(amount_fined, 'None'), ''),
    NULLIF(latitude, '')::DOUBLE PRECISION,
    NULLIF(longitude, '')::DOUBLE PRECISION,
    NULLIF(unique_id, 'None')
FROM _csv_staging;

-- Clean up
DROP TABLE _csv_staging;
```

- [ ] **Step 2: Commit**

```bash
git add db/init.sql
git commit -m "add database init script for CSV import"
```

---

### Task 2: Docker Compose

**Files:**
- Create: `docker-compose.yml`

**Context:** The `db` service mounts `db/Dinesafe.csv` into the container at `/data/` and `db/init.sql` into `/docker-entrypoint-initdb.d/`. The init script only runs on first startup (when the volume is empty). The `web` service waits for db to be healthy before starting.

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_USER: dinesafe
      POSTGRES_PASSWORD: dinesafe
      POSTGRES_DB: dinesafe
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./db/Dinesafe.csv:/data/Dinesafe.csv
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dinesafe"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: ./web
    ports:
      - "5000:5000"
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: dinesafe
      DB_USER: dinesafe
      DB_PASSWORD: dinesafe
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "add docker-compose with postgres and web services"
```

---

### Task 3: Flask web app

**Files:**
- Create: `web/requirements.txt`
- Create: `web/app.py`
- Create: `web/templates/index.html`
- Create: `web/Dockerfile`

- [ ] **Step 1: Create `web/requirements.txt`**

```
flask==3.1.1
psycopg2-binary==2.9.10
```

- [ ] **Step 2: Create `web/app.py`**

```python
import os

import psycopg2
from flask import Flask, render_template

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "dinesafe"),
    "user": os.environ.get("DB_USER", "dinesafe"),
    "password": os.environ.get("DB_PASSWORD", "dinesafe"),
}


@app.route("/")
def index():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT inspection_date, establishment_name, severity "
        "FROM inspections ORDER BY inspection_date DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    inspections = []
    for date, name, severity in rows:
        if severity:
            violation = f"Yes — {severity}"
        else:
            violation = "No"
        inspections.append({"date": date, "name": name, "violation": violation})

    return render_template("index.html", inspections=inspections)
```

- [ ] **Step 3: Create `web/templates/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DineSafeViz</title>
    <style>
        body { font-family: sans-serif; margin: 2rem; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; }
        th { background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>DineSafe Inspections</h1>
    {% if inspections %}
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Establishment</th>
                <th>Violations Found</th>
            </tr>
        </thead>
        <tbody>
            {% for row in inspections %}
            <tr>
                <td>{{ row.date }}</td>
                <td>{{ row.name }}</td>
                <td>{{ row.violation }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No data available.</p>
    {% endif %}
</body>
</html>
```

- [ ] **Step 4: Create `web/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["flask", "run", "--host=0.0.0.0"]
```

- [ ] **Step 5: Commit**

```bash
git add web/
git commit -m "add flask web app with inspection list page"
```

---

### Task 4: Smoke test

**Context:** Bring up the stack, verify the database loaded correctly, and check the web page renders.

- [ ] **Step 1: Build and start**

```bash
docker compose up --build -d
```

Wait for services to be healthy:

```bash
docker compose ps
```

Expected: both `db` and `web` show as running, `db` shows `healthy`.

- [ ] **Step 2: Verify database loaded**

```bash
docker compose exec db psql -U dinesafe -d dinesafe -c "SELECT count(*) FROM inspections;"
```

Expected: `18380` (18381 CSV rows minus the header).

- [ ] **Step 3: Verify web page**

```bash
curl -s http://localhost:5000 | head -20
```

Expected: HTML containing `<h1>DineSafe Inspections</h1>` and `<table>` with data rows.

- [ ] **Step 4: Verify violation logic**

```bash
docker compose exec db psql -U dinesafe -d dinesafe -c "SELECT severity, count(*) FROM inspections GROUP BY severity ORDER BY severity;"
```

Confirm there are rows with NULL severity (should show "No") and rows with values like `M - Minor`, `S - Significant`, `C - Crucial` (should show "Yes — ...").

- [ ] **Step 5: Commit journal update**

Update `docs/ref/journal/journal-1.md` with smoke test results, then commit.

```bash
git add docs/ref/journal/journal-1.md
git commit -m "update journal with smoke test results"
```
