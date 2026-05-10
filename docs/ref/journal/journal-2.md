# Journal 2 — Implement DineSafeViz PoC

## 2026-04-26 — Session start

### Context
- Branch: `4-setup-a-db`
- Goal: Execute implementation plan — DB init script, Docker Compose, Flask app, smoke test
- Plan: `docs/superpowers/plans/2026-04-26-poc-implementation.md`
- Spec: `docs/superpowers/specs/2026-04-26-poc-design.md`
- Existing: `db/Dinesafe.csv` present, no other app files yet

### 2026-04-26 — Task 1: Database init script

- Created `db/init.sql` with staging table approach
- Staging table (`_csv_staging`) loads all 17 CSV columns as TEXT
- Final `inspections` table uses explicit casts and `NULLIF` to convert `'None'`/empty strings to actual NULLs
- `amount_fined` gets double NULLIF (handles both `'None'` and `''`)
- `latitude`/`longitude` only need empty-string NULLIF since they're numeric fields that wouldn't contain the string `'None'`

### 2026-04-26 — Task 2: Docker Compose

- Created `docker-compose.yml` with `db` and `web` services
- `db` mounts `init.sql` into `/docker-entrypoint-initdb.d/` (auto-runs on first start) and `Dinesafe.csv` into `/data/`
- `web` depends on `db` being healthy via `pg_isready` healthcheck (5s interval, 5 retries)
- Named volume `dsv-db-data` persists DB data across container restarts

### 2026-04-26 — Task 3: Flask web app

- Created `web/requirements.txt`: flask 3.1.1, psycopg2-binary 2.9.10
- Created `web/app.py`: single route `/`, queries inspections ordered by date DESC, maps NULL/falsy severity to "No", non-null to "Yes — {severity}"
- Created `web/templates/index.html`: Jinja2 table with empty-state fallback
- Created `web/Dockerfile`: python:3.12-slim, requirements installed before code copy for layer caching

### 2026-04-26 — Task 4: Smoke test (blocked)

- Attempted `docker compose up --build -d` — Docker not in PATH in this environment
- Smoke test must be run manually in a terminal with Docker available
- All 3 implementation tasks are committed and ready to test
- Commands to run:
  ```
  docker compose up --build -d
  docker compose ps
  docker compose exec db psql -U dinesafe -d dinesafe -c "SELECT count(*) FROM inspections;"
  curl -s http://localhost:5000 | head -20
  docker compose exec db psql -U dinesafe -d dinesafe -c "SELECT severity, count(*) FROM inspections GROUP BY severity ORDER BY severity;"
  ```
- Expected: 18380 rows, HTML with table, NULL severity rows (show "No") and M/S/C severity rows (show "Yes — ...")

