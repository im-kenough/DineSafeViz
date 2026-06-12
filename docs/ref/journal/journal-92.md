# Journal 92

## 2026-06-11 — Task 8: Smoke test

### Context
Tasks 1–7 are complete (HEAD: 3f7a06d). Running full stack bring-up and
verifying all new features end-to-end.

New features under test:
- Health endpoints: /healthz, /readyz
- Prometheus metrics: /metrics
- X-Request-ID header (UUID injected by app)
- JSON structured logs from dsv-app
- OTel span JSON in logs
- Non-root user (uid=65532 nonroot)
- nginx as entry point (Server: nginx/... header)

### Pre-flight: .env missing

No `.env` file existed (gitignored). The task description warned this was a
possible failure mode. Created `/home/sam/SCM/github/DineSafeViz/.env` with
sensible test credentials matching init.sql:
- DSV_DB_USER=postgres / DSV_DB_PASSWORD=postgres (superuser for Postgres init)
- DSV_DB_NAME=dinesafe / DSV_DB_PORT=5432
- DSV_ANALYTICS_ADMIN_USER=admin / DSV_ANALYTICS_ADMIN_PASSWORD=admin

Also had to add `--env-file` flag to all docker compose commands — when using
`-f` with an absolute path, docker compose does not auto-load `.env` from the
project root unless run from that directory (which the sandbox doesn't preserve).

### Step 1: Rebuild and start

Build: SUCCESS. All packages installed, image built as two-stage (build +
runtime). Final image: `dsv-dsv-app:latest`.

Stack up: SUCCESS. All 6 containers started. dsv-db became healthy before
dependent services started.

### Step 1b: Init container results

- `dsv-init-analytics`: Exited (0) — Grafana dashboard permissions set OK.
- `dsv-init-db`: Exited (1) — HTTP 404 fetching the Toronto Open Data CSV.
  This is an external data dependency failure (the upstream CSV URL returned
  404), not a code defect. The DB is empty but the app still runs.

### Step 2: Health checks

- `/healthz` → `ok` ✓
- `/readyz` → `ok` ✓ (DB connected fine despite empty tables)
- `/metrics` → Prometheus text format, first 20 lines include python_gc_*
  counters and python_info ✓

### Step 3: X-Request-ID header

Response: `X-Request-ID: f63eb307-4b11-44ef-a33a-040e77a4f377` ✓

### Step 4: JSON logs

JSON log lines confirmed with all expected fields:
```
{"asctime": "...", "name": "dsv-app", "levelname": "INFO", "message": "request",
 "request_id": "...", "route": "home", "method": "GET", "status": 200,
 "duration_ms": 124.55, "remote_addr": "...", "user_agent": "curl/..."}
```
Routes logged: healthz, readyz, prometheus_metrics, home ✓

### Step 5: OTel spans

Span names visible in log output:
- `"name": "GET /healthz"`
- `"name": "SELECT"`
Both present as console-exported JSON objects ✓

### Step 6: Non-root user

`uid=65532(nonroot) gid=65532(nonroot) groups=65532(nonroot)` ✓

### Step 7: nginx entry point

`Server: nginx/1.30.2` ✓

### Step 8: Tear down

All containers, network, and volumes removed cleanly ✓

