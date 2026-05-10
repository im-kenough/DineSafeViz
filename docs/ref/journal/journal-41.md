# Journal 41

## 2026-05-09 12:00 — Review and update docs/ref/arch.md

**Task:** Review the repo and rewrite `docs/ref/arch.md` to be accurate and
provide a high-level architectural overview.

**Files read:**
- `docker-compose.yml` — authoritative source for services, images, ports, env vars
- `src/dsv-db/init.sql` — creates table schema only; no data loading
- `src/dsv-db/Dockerfile` — uses `python:3.14-slim`, runs `refresh.py`
- `src/dsv-db/refresh.py` — handles seeding + daily refresh by downloading from Toronto Open Data APIs
- `src/dsv-app/app.py` — 4 routes + analytics reverse proxy
- `docs/ref/data.md` — data schema, sources, ingestion details

**Issues found in existing arch.md:**

1. CSV loading was described as `init.sql` + COPY from a bind-mounted
   `/data/Dinesafe.csv`. Wrong — `init.sql` only creates the table. Data
   loading is done by `refresh.py` which downloads from Toronto Open Data.
   The bind mount for the CSV is not in `docker-compose.yml`.

2. Postgres image listed as `postgres:17`; actual is `postgres:17.9`.

3. Web app described as "single page at `/`". Wrong — there are 4 routes:
   `/`, `/inspections`, `/dashboard`, `/info`, plus an analytics reverse
   proxy at `/analytics/<path>`.

4. The query and "Violations Found" display logic described were from an
   older version of the app.

5. `dsv-init-db` / `dsv-init-analytics` description merged the two services
   and was vague.

6. File layout was significantly out of date — missing static/, tests/,
   refresh.py, Dockerfile in dsv-db, etc.

7. Configuration section missing analytics env vars
   (`DSV_ANALYTICS_URL`, `DSV_ANALYTICS_ROOT_URL`,
   `DSV_ANALYTICS_ADMIN_USER`, `DSV_ANALYTICS_ADMIN_PASSWORD`).

8. Link `[data](../data.md)` pointed to `docs/data.md` (does not exist);
   correct relative path is `data.md` (same directory).

**Decision:** Rewrote arch.md with a high-level overview, removing
implementation-specific details (exact SQL, column lists) that belong
in `data.md` and can drift out of sync. Focused on service topology,
data flow, routes, and configuration.
