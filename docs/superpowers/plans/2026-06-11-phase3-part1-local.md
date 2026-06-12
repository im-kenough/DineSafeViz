# Phase 3 Part 1 — Local Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Flask webapp with health endpoints, Prometheus metrics, JSON logging, request IDs, OpenTelemetry SDK, gunicorn, a multi-stage Dockerfile, a least-privilege DB role, and an nginx reverse proxy replacing the in-app analytics proxy — all runnable with `docker compose up`.

**Architecture:** Seven sequential tasks, each independently committable. Tasks 1–4 are pure `app.py` additions. Task 5 replaces the Dockerfile and adds gunicorn. Task 6 splits the DB role in SQL. Task 7 removes the Flask reverse proxy and routes `/analytics/*` through a new nginx service.

**Tech Stack:** Flask 3, gunicorn, prometheus-flask-exporter, python-json-logger, opentelemetry-sdk, psycopg2-binary, nginx:stable-alpine, postgres:17, Python 3.12-slim-bookworm

---

## Scope notes (vs. the Phase 3 spec)

The spec targets AKS. This plan defers the following to the AKS deployment:
- **Distroless final image** — local Dockerfile uses `python:3.12-slim-bookworm` with a non-root user; the AKS image switches to `gcr.io/distroless/python3-debian12:nonroot`.
- **`readOnlyRootFilesystem` + emptyDir volumes** — Kubernetes pod security context; not needed in compose.
- **CNPG Pooler (PgBouncer)** — CNPG is a Kubernetes operator. The DB role split is implemented, but no PgBouncer is added locally.
- **OTel OTLP exporter** — console exporter only in Part 1; OTLP wiring is Part 2.
- **gunicorn `workers = 1`** — local only; avoids prometheus multiprocess complexity. Production uses 4 workers with `PROMETHEUS_MULTIPROC_DIR`.

---

## File map

**Modified:**
- `src/dsv-app/app.py` — add health endpoints, metrics, logging, request IDs, OTel; remove analytics proxy
- `src/dsv-app/requirements.txt` — add gunicorn, prometheus-flask-exporter, python-json-logger, opentelemetry packages; remove `requests`
- `src/dsv-app/Dockerfile` — multi-stage non-root build
- `src/dsv-db/init.sql` — add `dinesafe_app` and `dinesafe_migrator` roles
- `docker-compose.yml` — add nginx service; update dsv-app port/env/deps; update analytics ROOT_URL

**Created:**
- `src/dsv-app/gunicorn.conf.py`
- `src/dsv-nginx/nginx.conf`
- `src/dsv-app/tests/test_health.py`

**Deleted:**
- `src/dsv-app/tests/test_proxy.py` — proxy route is removed in Task 7

---

## Baseline

Before starting, confirm existing tests pass:

```bash
cd src/dsv-app
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -q
```

Expected: all tests pass. If they don't, fix them first.

---

## Task 1: Health endpoints

**Files:**
- Create: `src/dsv-app/tests/test_health.py`
- Modify: `src/dsv-app/app.py`

- [ ] **Step 1: Write failing tests**

Create `src/dsv-app/tests/test_health.py`:

```python
import uuid
from unittest.mock import MagicMock, patch


def test_healthz_returns_200(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.data == b"ok"


def test_readyz_returns_200_when_db_ok(client):
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = MagicMock()
    with patch("app.psycopg2.connect", return_value=mock_conn):
        resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.data == b"ok"


def test_readyz_returns_503_when_db_fails(client):
    with patch("app.psycopg2.connect", side_effect=Exception("connection refused")):
        resp = client.get("/readyz")
    assert resp.status_code == 503
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd src/dsv-app && pytest tests/test_health.py -v
```

Expected: 3 failures — `404 != 200` (routes don't exist yet).

- [ ] **Step 3: Add routes to `app.py`**

Add after the `info()` route (before line 303, the analytics proxy section):

```python
@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/readyz")
def readyz():
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=1)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return "ok", 200
    except Exception:
        return "db unreachable", 503
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd src/dsv-app && pytest tests/test_health.py tests/test_routes.py tests/test_home.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/dsv-app/app.py src/dsv-app/tests/test_health.py
git commit -m "feat: add /healthz and /readyz health endpoints"
```

---

## Task 2: Prometheus metrics

**Files:**
- Modify: `src/dsv-app/requirements.txt`
- Modify: `src/dsv-app/app.py`

- [ ] **Step 1: Add dependency**

In `src/dsv-app/requirements.txt`, add:

```
prometheus-flask-exporter==0.23.1
```

Install: `pip install -r requirements.txt`

- [ ] **Step 2: Add metrics init to `app.py`**

Add these imports at the top of `app.py` (after the existing `import` block, before `app = Flask(__name__)`):

```python
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram
```

After `app = Flask(__name__)`, add:

```python
metrics = PrometheusMetrics(app)
_db_query_duration = Histogram(
    "dsv_db_query_duration_seconds", "DB query latency", ["route"]
)
_stats_cache_hits = Counter("dsv_stats_cache_hits_total", "Stats cache hits")
_stats_cache_misses = Counter("dsv_stats_cache_misses_total", "Stats cache misses")
_inspection_rows_returned = Histogram(
    "dsv_inspection_rows_returned", "Inspection rows per /inspections request"
)
```

- [ ] **Step 3: Instrument `_get_home_stats()`**

Replace the existing cache-check and DB query block in `_get_home_stats()`:

```python
def _get_home_stats() -> Dict[str, int]:
    now = datetime.now()
    if (
        _stats_cache["fetched_at"] is not None
        and now - _stats_cache["fetched_at"] <= _STATS_TTL
    ):
        _stats_cache_hits.inc()
        return _stats_cache["data"]

    _stats_cache_misses.inc()
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        with _db_query_duration.labels(route="home").time():
            cur.execute(
                "SELECT COUNT(*), MIN(inspection_date), MAX(inspection_date) FROM inspections"
            )
            total, min_date, max_date = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    years_of_data = 0
    if min_date is not None and max_date is not None:
        years_of_data = max_date.year - min_date.year + 1

    stats = {"total_inspections": total, "years_of_data": years_of_data}
    _stats_cache["data"] = stats
    _stats_cache["fetched_at"] = now
    return stats
```

- [ ] **Step 4: Instrument `index()`**

Replace the DB query block in `index()`:

```python
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    with _db_query_duration.labels(route="inspections").time():
        cur.execute(
            "SELECT inspection_date, establishment_status, action, infraction_details,"
            "       establishment_name, establishment_address, establishment_type,"
            "       outcome, outcome_date, amount_fined"
            " FROM inspections"
            " WHERE inspection_date BETWEEN %s AND %s",
            (start, end),
        )
        raw_rows = cur.fetchall()
    cur.close()
    conn.close()
    _inspection_rows_returned.observe(len(raw_rows))

    rows = [
        {
            "inspection_date": r[0],
            "establishment_status": r[1],
            "action": r[2],
            "infraction_details": r[3],
            "establishment_name": r[4],
            "establishment_address": r[5],
            "establishment_type": r[6],
            "outcome": r[7],
            "outcome_date": r[8],
            "amount_fined": r[9],
        }
        for r in raw_rows
    ]
```

Note: the `rows` variable name in the return statement below also needs updating from `rows` to use the new `rows` local variable — the names stay the same, so no change needed in `render_template`.

- [ ] **Step 5: Run full test suite**

```bash
cd src/dsv-app && pytest tests/ -q
```

Expected: all pass. The `/metrics` endpoint is auto-created by `PrometheusMetrics`.

- [ ] **Step 6: Commit**

```bash
git add src/dsv-app/requirements.txt src/dsv-app/app.py
git commit -m "feat: add prometheus metrics endpoint and custom dsv_* metrics"
```

---

## Task 3: Structured JSON logging + request IDs

**Files:**
- Modify: `src/dsv-app/requirements.txt`
- Modify: `src/dsv-app/app.py`
- Modify: `src/dsv-app/tests/test_health.py`

- [ ] **Step 1: Add dependency**

In `src/dsv-app/requirements.txt`, add:

```
python-json-logger==3.3.0
```

Install: `pip install -r requirements.txt`

- [ ] **Step 2: Add logging setup to `app.py`**

Add these imports:

```python
import logging
import time
import uuid
from pythonjsonlogger import jsonlogger
from flask import Flask, g, render_template, request
```

(Replace the existing `from flask import Flask, render_template, request` line with the version that also imports `g`.)

After `app = Flask(__name__)` (but before `metrics = PrometheusMetrics(app)`), add:

```python
_logger = logging.getLogger("dsv-app")
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(
    jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
)
_logger.addHandler(_log_handler)
_logger.setLevel(logging.INFO)
```

- [ ] **Step 3: Add `before_request` and `after_request` hooks**

Add after `_VERSION = _read_version()` and before `@app.context_processor`:

```python
@app.before_request
def _before_request():
    g.request_id = str(uuid.uuid4())
    g.start_time = time.monotonic()


@app.after_request
def _after_request(response):
    duration_ms = round((time.monotonic() - g.start_time) * 1000, 2)
    _logger.info(
        "request",
        extra={
            "request_id": g.request_id,
            "route": request.endpoint,
            "method": request.method,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "remote_addr": request.remote_addr,
            "user_agent": request.user_agent.string,
        },
    )
    response.headers["X-Request-ID"] = g.request_id
    return response
```

- [ ] **Step 4: Add request ID tests to `test_health.py`**

Append to `src/dsv-app/tests/test_health.py`:

```python
def test_request_id_header_present(client):
    resp = client.get("/healthz")
    assert "X-Request-ID" in resp.headers


def test_request_id_is_valid_uuid(client):
    resp = client.get("/healthz")
    uuid.UUID(resp.headers["X-Request-ID"])  # raises ValueError if invalid
```

- [ ] **Step 5: Run tests**

```bash
cd src/dsv-app && pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dsv-app/requirements.txt src/dsv-app/app.py src/dsv-app/tests/test_health.py
git commit -m "feat: structured JSON logging and per-request X-Request-ID header"
```

---

## Task 4: OpenTelemetry SDK (console exporter)

**Files:**
- Modify: `src/dsv-app/requirements.txt`
- Modify: `src/dsv-app/app.py`

- [ ] **Step 1: Add dependencies**

In `src/dsv-app/requirements.txt`, add:

```
opentelemetry-distro==0.51b0
opentelemetry-instrumentation-flask==0.51b0
opentelemetry-instrumentation-psycopg2==0.51b0
```

Install: `pip install -r requirements.txt`

> If `0.51b0` is unavailable, run `pip install opentelemetry-distro opentelemetry-instrumentation-flask opentelemetry-instrumentation-psycopg2` and pin the installed versions: `pip freeze | grep opentelemetry`.

- [ ] **Step 2: Add OTel setup to `app.py`**

Add these imports:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
```

After the prometheus metrics block (after `_inspection_rows_returned = Histogram(...)`), add:

```python
_otel_provider = TracerProvider()
_otel_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(_otel_provider)
FlaskInstrumentor().instrument_app(app)
Psycopg2Instrumentor().instrument()
```

- [ ] **Step 3: Run tests**

```bash
cd src/dsv-app && pytest tests/ -q
```

Expected: all pass. OTel span output will appear on stdout during the test run — that's expected behaviour (console exporter).

- [ ] **Step 4: Commit**

```bash
git add src/dsv-app/requirements.txt src/dsv-app/app.py
git commit -m "feat: add OpenTelemetry SDK with console exporter (Part 2 will wire OTLP)"
```

---

## Task 5: gunicorn + multi-stage Dockerfile

**Files:**
- Modify: `src/dsv-app/requirements.txt`
- Create: `src/dsv-app/gunicorn.conf.py`
- Modify: `src/dsv-app/Dockerfile`

> **AKS note:** The AKS deployment uses `gcr.io/distroless/python3-debian12:nonroot` as the final stage. The local Dockerfile uses `python:3.12-slim-bookworm` for simplicity; the `nonroot` user (UID 65532) matches the distroless convention so the two are drop-in compatible.

- [ ] **Step 1: Add gunicorn to `requirements.txt`**

```
gunicorn==23.0.0
```

- [ ] **Step 2: Create `src/dsv-app/gunicorn.conf.py`**

```python
workers = 1          # local only; production: 4 with PROMETHEUS_MULTIPROC_DIR set
worker_class = "gthread"
threads = 4
timeout = 30
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
preload_app = True
bind = "0.0.0.0:8000"
```

- [ ] **Step 3: Rewrite `src/dsv-app/Dockerfile`**

```dockerfile
FROM python:3.12-slim-bookworm AS build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 65532 nonroot \
 && useradd --uid 65532 --gid 65532 --no-create-home nonroot
WORKDIR /app
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --chown=nonroot:nonroot . .
USER nonroot:nonroot
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
```

- [ ] **Step 4: Build and verify**

```bash
docker build -t dsv-app-test src/dsv-app/
docker run --rm -e DSV_DB_HOST=fake -e DSV_DB_PASSWORD=fake dsv-app-test gunicorn --check-config -c gunicorn.conf.py app:app
```

Expected: exits 0 (config is valid). The app will fail to start without a DB, but config validation passes.

- [ ] **Step 5: Commit**

```bash
git add src/dsv-app/requirements.txt src/dsv-app/gunicorn.conf.py src/dsv-app/Dockerfile
git commit -m "feat: gunicorn app server and multi-stage non-root Dockerfile"
```

---

## Task 6: Database role split

**Files:**
- Modify: `src/dsv-db/init.sql`
- Modify: `docker-compose.yml`

The postgres superuser (`${DSV_DB_USER}`) stays unchanged and is used only for DB setup (via `dsv-init-db`). The Flask app connects as the new `dinesafe_app` role.

- [ ] **Step 1: Update `src/dsv-db/init.sql`**

Replace the entire file with:

```sql
CREATE ROLE dinesafe_migrator WITH LOGIN PASSWORD 'dinesafe_migrator';
CREATE ROLE dinesafe_app      WITH LOGIN PASSWORD 'dinesafe_app';

CREATE TABLE inspections (
    id                          SERIAL PRIMARY KEY,
    establishment_id            TEXT,
    inspection_id               TEXT,
    establishment_name          TEXT,
    establishment_type          TEXT,
    establishment_address       TEXT,
    infraction_details          TEXT,
    inspection_observation      TEXT,
    inspection_date             DATE,
    severity                    TEXT,
    action                      TEXT,
    outcome                     TEXT,
    outcome_date                TEXT,
    amount_fined                TEXT,
    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
    unique_id                   TEXT,
    establishment_status        TEXT,
    min_inspections_per_year    TEXT
);

GRANT CONNECT ON DATABASE dinesafe TO dinesafe_app;
GRANT USAGE   ON SCHEMA public       TO dinesafe_app;
GRANT SELECT, INSERT, UPDATE ON TABLE inspections TO dinesafe_app;

GRANT CONNECT ON DATABASE dinesafe TO dinesafe_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO dinesafe_migrator;
GRANT ALL PRIVILEGES ON TABLE inspections TO dinesafe_migrator;
GRANT ALL PRIVILEGES ON SEQUENCE inspections_id_seq TO dinesafe_migrator;
```

- [ ] **Step 2: Update `docker-compose.yml` — dsv-app env block**

Change the `dsv-app` service environment so it connects as `dinesafe_app`:

```yaml
  dsv-app:
    build: ./src/dsv-app
    environment:
      DSV_DB_HOST: dsv-db
      DSV_DB_PORT: ${DSV_DB_PORT}
      DSV_DB_NAME: ${DSV_DB_NAME}
      DSV_DB_USER: ${DSV_DB_APP_USER:-dinesafe_app}
      DSV_DB_PASSWORD: ${DSV_DB_APP_PASSWORD:-dinesafe_app}
```

The `dsv-db` postgres service keeps `POSTGRES_USER: ${DSV_DB_USER}` (unchanged — superuser for init).

The `dsv-analytics` (Grafana) service also queries Postgres; update its credentials to use `dinesafe_app` as well:

```yaml
  dsv-analytics:
    ...
    environment:
      ...
      DSV_DB_USER: ${DSV_DB_APP_USER:-dinesafe_app}
      DSV_DB_PASSWORD: ${DSV_DB_APP_PASSWORD:-dinesafe_app}
```

- [ ] **Step 3: Re-seed the database**

```bash
docker compose down -v   # removes the old dsv-db-data volume
docker compose up dsv-db dsv-init-db --wait
```

Expected: DB starts, init-db runs, exits 0.

- [ ] **Step 4: Verify role exists**

```bash
docker compose exec dsv-db psql -U dinesafe -d dinesafe -c "\du"
```

Expected: `dinesafe_app` and `dinesafe_migrator` appear in the role list.

- [ ] **Step 5: Commit**

```bash
git add src/dsv-db/init.sql docker-compose.yml
git commit -m "feat: split DB into dinesafe_app (CRUD) and dinesafe_migrator (DDL) roles"
```

---

## Task 7: nginx routing + analytics proxy removal

**Files:**
- Create: `src/dsv-nginx/nginx.conf`
- Modify: `docker-compose.yml`
- Modify: `src/dsv-app/app.py`
- Modify: `src/dsv-app/requirements.txt`
- Delete: `src/dsv-app/tests/test_proxy.py`

The Flask app no longer proxies `/analytics/*`. An nginx container routes `/analytics/*` to `dsv-analytics:3000` and everything else to `dsv-app:8000`. The app is no longer exposed externally; nginx is the only external entry point on port **8080**.

- [ ] **Step 1: Create `src/dsv-nginx/nginx.conf`**

```nginx
events {}

http {
    server {
        listen 80;

        location /analytics/ {
            proxy_pass         http://dsv-analytics:3000;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade $http_upgrade;
            proxy_set_header   Connection "upgrade";
            proxy_set_header   Host $http_host;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location / {
            proxy_pass         http://dsv-app:8000;
            proxy_set_header   Host $http_host;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
        }
    }
}
```

- [ ] **Step 2: Update `docker-compose.yml`**

Replace the entire `docker-compose.yml` with:

```yaml
name: dsv

services:
  dsv-nginx:
    image: nginx:stable-alpine
    ports:
      - "8080:80"
    volumes:
      - ./src/dsv-nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      dsv-app:
        condition: service_started
      dsv-analytics:
        condition: service_started

  dsv-app:
    build: ./src/dsv-app
    environment:
      DSV_DB_HOST: dsv-db
      DSV_DB_PORT: ${DSV_DB_PORT}
      DSV_DB_NAME: ${DSV_DB_NAME}
      DSV_DB_USER: ${DSV_DB_APP_USER:-dinesafe_app}
      DSV_DB_PASSWORD: ${DSV_DB_APP_PASSWORD:-dinesafe_app}
    depends_on:
      dsv-db:
        condition: service_healthy

  dsv-db:
    image: postgres:17.0
    environment:
      POSTGRES_USER: ${DSV_DB_USER}
      POSTGRES_PASSWORD: ${DSV_DB_PASSWORD}
      POSTGRES_DB: ${DSV_DB_NAME}
    volumes:
      - dsv-db-data:/var/lib/postgresql/data
      - ./src/dsv-db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DSV_DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  dsv-init-db:
    build: ./src/dsv-db
    environment:
      DSV_DB_HOST: dsv-db
      DSV_DB_PORT: ${DSV_DB_PORT}
      DSV_DB_NAME: ${DSV_DB_NAME}
      DSV_DB_USER: ${DSV_DB_USER}
      DSV_DB_PASSWORD: ${DSV_DB_PASSWORD}
    depends_on:
      dsv-db:
        condition: service_healthy
    restart: "no"

  dsv-analytics:
    image: grafana/grafana:11.2.0
    ports:
      - "3000:3000"
    environment:
      GF_SERVER_ROOT_URL: ${DSV_ANALYTICS_ROOT_URL:-http://localhost:8080/analytics/}
      GF_SERVER_SERVE_FROM_SUB_PATH: "true"
      GF_SECURITY_ADMIN_USER: ${DSV_ANALYTICS_ADMIN_USER}
      GF_SECURITY_ADMIN_PASSWORD: ${DSV_ANALYTICS_ADMIN_PASSWORD}
      GF_SECURITY_ALLOW_EMBEDDING: "true"
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
      GF_USERS_VIEWERS_CAN_EDIT: "true"
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /etc/grafana/provisioning/dashboards/dinesafe.json
      DSV_DB_HOST: dsv-db
      DSV_DB_PORT: ${DSV_DB_PORT}
      DSV_DB_NAME: ${DSV_DB_NAME}
      DSV_DB_USER: ${DSV_DB_APP_USER:-dinesafe_app}
      DSV_DB_PASSWORD: ${DSV_DB_APP_PASSWORD:-dinesafe_app}
    volumes:
      - ./src/dsv-analytics/provisioning:/etc/grafana/provisioning
      - dsv-analytics-data:/var/lib/grafana
    depends_on:
      dsv-db:
        condition: service_healthy

  dsv-init-analytics:
    image: curlimages/curl:latest
    depends_on:
      dsv-analytics:
        condition: service_started
    environment:
      DSV_ANALYTICS_ADMIN_USER: ${DSV_ANALYTICS_ADMIN_USER}
      DSV_ANALYTICS_ADMIN_PASSWORD: ${DSV_ANALYTICS_ADMIN_PASSWORD}
    entrypoint:
      - sh
      - -c
      - |
        i=0; until curl -s http://dsv-analytics:3000/analytics/api/health | grep -q '"database": "ok"'; do sleep 2; i=$$(($$i+1)); [ $$i -ge 30 ] && echo "Analytics dashboard did not start in time" && exit 1; done
        DASH_ID=$$(curl -s "http://$$DSV_ANALYTICS_ADMIN_USER:$$DSV_ANALYTICS_ADMIN_PASSWORD@dsv-analytics:3000/analytics/api/dashboards/uid/dinesafe" | grep -oE '"id":[0-9]+' | head -1 | grep -oE '[0-9]+')
        [ -z "$$DASH_ID" ] && echo "Dashboard not found, skipping permissions grant" && exit 0
        curl -sf -X POST "http://$$DSV_ANALYTICS_ADMIN_USER:$$DSV_ANALYTICS_ADMIN_PASSWORD@dsv-analytics:3000/analytics/api/dashboards/id/$$DASH_ID/permissions" -H "Content-Type: application/json" -d '{"items":[{"role":"Viewer","permission":1}]}'
    restart: "no"

volumes:
  dsv-db-data:
  dsv-analytics-data:
```

- [ ] **Step 3: Remove the analytics proxy from `app.py`**

Delete these lines from `app.py`:

```python
import requests as http_requests   # the import at the top
```

```python
DSV_ANALYTICS_URL = os.environ.get("DSV_ANALYTICS_URL", "http://dsv-analytics:3000")
_analytics_session = http_requests.Session()
_HOP_BY_HOP = {"content-encoding", "content-length", "transfer-encoding", "connection"}


@app.route("/analytics/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.route("/analytics/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def analytics_proxy(path):
    """Reverse-proxy requests to the internal analytics container."""
    url = f"{DSV_ANALYTICS_URL}/analytics/{path}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    resp = _analytics_session.request(
        method=request.method,
        url=url,
        headers={k: v for k, v in request.headers if k.lower() != "host"},
        data=request.get_data(),
        allow_redirects=False,
    )
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in _HOP_BY_HOP}
    return resp.content, resp.status_code, headers
```

- [ ] **Step 4: Remove `requests` from `requirements.txt`**

Delete: `requests==2.34.2`

- [ ] **Step 5: Delete `test_proxy.py`**

```bash
rm src/dsv-app/tests/test_proxy.py
```

- [ ] **Step 6: Run tests**

```bash
cd src/dsv-app && pip install -r requirements.txt && pytest tests/ -q
```

Expected: all pass. No proxy tests remain.

- [ ] **Step 7: Commit**

```bash
git add src/dsv-nginx/nginx.conf docker-compose.yml src/dsv-app/app.py src/dsv-app/requirements.txt
git rm src/dsv-app/tests/test_proxy.py
git commit -m "feat: replace Flask analytics proxy with nginx routing; add dsv-nginx service"
```

---

## Task 8: Smoke test

Full stack bring-up and verification.

- [ ] **Step 1: Rebuild and start**

```bash
docker compose down -v
docker compose build dsv-app
docker compose up -d
```

Wait ~30s for `dsv-init-db` and `dsv-init-analytics` to complete.

- [ ] **Step 2: Health checks**

```bash
curl -s http://localhost:8080/healthz                     # → ok
curl -s http://localhost:8080/readyz                      # → ok (or 503 if DB not ready; retry)
curl -s http://localhost:8080/metrics | head -20           # → prometheus text format
```

- [ ] **Step 3: Request ID header**

```bash
curl -si http://localhost:8080/ | grep X-Request-ID
```

Expected: `X-Request-ID: <uuid>`

- [ ] **Step 4: JSON logs**

```bash
docker compose logs dsv-app --tail=5
```

Expected: lines like `{"asctime": "...", "name": "dsv-app", "levelname": "INFO", "message": "request", "request_id": "...", "route": "home", ...}`

- [ ] **Step 5: OTel spans**

```bash
docker compose logs dsv-app | grep '"name": "/"'
```

Expected: JSON OTel span objects in the log output.

- [ ] **Step 6: Analytics dashboard via nginx**

Open `http://localhost:8080/dashboard` in a browser. The Grafana iframe should load.

Direct Grafana access (still exposed for dev convenience): `http://localhost:3000/analytics/`

- [ ] **Step 7: Confirm app runs as non-root**

```bash
docker compose exec dsv-app id
```

Expected: `uid=65532(nonroot) gid=65532(nonroot)`

---

## Running locally: quick reference

```bash
# First run (builds images, seeds DB, provisions Grafana):
docker compose up --build

# App:       http://localhost:8080
# Grafana:   http://localhost:8080/analytics/  (via nginx)
#            http://localhost:3000/analytics/  (direct, dev only)
# Metrics:   http://localhost:8080/metrics
# Healthz:   http://localhost:8080/healthz
# Readyz:    http://localhost:8080/readyz

# Subsequent runs:
docker compose up

# Tear down (preserves volumes):
docker compose down

# Tear down + reset DB:
docker compose down -v
```
