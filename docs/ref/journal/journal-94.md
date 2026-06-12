# Journal 94

## 2026-06-11 — `/simplify @src/` (high-effort review with --fix)

Running the recall-biased high-effort review skill on `src/`. Scope is
the diff `git diff @{upstream}...HEAD` filtered to `src/`. Working tree
only has doc edits, so out of scope.

Starting by capturing the diff scope and counting hunks per file before
launching the finder angles.

## 2026-06-11 — diff scope

`git diff @{upstream}...HEAD --stat -- src/` shows 9 files, 237 insertions,
111 deletions. Major themes: observability uplift (Prom + JSON logs + OTel +
health endpoints), runtime hardening (multi-stage non-root Dockerfile,
gunicorn, .dockerignore), and the Flask analytics proxy → nginx routing move.

## 2026-06-11 — finder angles dispatched

Dispatched 7 finder agents in parallel (A line-by-line, B removed-behavior,
C cross-file tracer, D reuse, E simplification, F efficiency, G altitude).
Aggregated and verified candidates inline; cross-checked a few that touch
files outside src/ (docker-compose.yml, refresh.py) before locking in the
top-10 list.

## 2026-06-11 — top 10 findings (recall-biased)

1. `src/dsv-app/app.py:320` — `index()` opens psycopg2.connect without
   `connect_timeout`; DB partition exhausts gthread workers while /healthz
   still says 200.
2. `src/dsv-app/app.py:62` — `_stats_cache` race under gthread; cold cache
   stampedes the DB on concurrent /home requests.
3. `src/dsv-db/init.sql:1` — role passwords hardcoded; `DSV_DB_APP_PASSWORD`
   env override silently breaks auth.
4. `src/dsv-nginx/nginx.conf:17` — `/metrics` publicly proxied to dsv-app via
   `location /`; leaks internal telemetry.
5. `src/dsv-nginx/nginx.conf:11` — `Connection "upgrade"` set unconditionally
   on `/analytics/`; non-WS Grafana requests lose keepalive.
6. `src/dsv-app/app.py:42` — `_inspection_rows_returned` histogram uses
   default buckets (max 10); every observation lands in +Inf.
7. `src/dsv-db/init.sql:35` — `ALTER DEFAULT PRIVILEGES` only covers
   `dinesafe_migrator` via `SET ROLE`, but `refresh.py:138` still connects
   as the superuser; default-privs block is dead-code for future tables.
8. `src/dsv-nginx/nginx.conf:22` — duplicate proxy_set_header has drifted:
   `/` has `X-Forwarded-Proto`, `/analytics/` does not.
9. `docker-compose.yml:25` — healthcheck targets `/healthz` (no DB touch),
   so nginx's `depends_on: dsv-app:service_healthy` can flip ready before
   the DB is reachable. `/readyz` is the right probe.
10. `src/dsv-app/app.py:169` — `g.request_id` is a fresh uuid4 even though
    FlaskInstrumentor already produces a W3C `trace_id`; correlation goal
    of the OTel work is defeated.

## 2026-06-11 — fixes applied

Surgical fixes for findings 1, 2, 4, 5, 6, 7, 8:

- `src/dsv-app/app.py`:
  - `connect_timeout=5` on both `psycopg2.connect` calls in `_get_home_stats`
    and `index()` (matches the pattern already in `/readyz`).
  - `threading.Lock` + double-check pattern around `_stats_cache` fill, so
    only one thread runs the COUNT(*) on cold cache.
  - Explicit `buckets=(100, 500, 1000, 5000, 10000, 50000)` on the inspection
    row-count histogram so the metric carries useful distribution.
- `src/dsv-nginx/nginx.conf`:
  - Added `map $http_upgrade $connection_upgrade { default upgrade; '' close; }`
    at http scope; `/analytics/` now uses `$connection_upgrade` so non-WS
    requests keep keepalive.
  - Added `location = /metrics { return 404; }` to block public prometheus
    scrape path. No internal scraper consumes it yet, so blocking now costs
    nothing.
  - Added `X-Forwarded-Proto $scheme` to `/analytics/` (was already on `/`).
- `src/dsv-db/init.sql`:
  - Replaced `SET ROLE dinesafe_migrator; ALTER DEFAULT PRIVILEGES …;
    RESET ROLE;` with `ALTER DEFAULT PRIVILEGES FOR ROLE dinesafe,
    dinesafe_migrator …` so tables created by either the superuser
    (refresh.py today) OR the migrator role auto-grant SELECT to dinesafe_app.

Skipped, with reasons:

- Finding 3 (init.sql hardcoded passwords): Postgres
  `/docker-entrypoint-initdb.d/*.sql` files are not envsubst'd; a fix requires
  a shell wrapper or restructuring how role creation runs. Out of surgical
  scope — flagged but not fixed.
- Finding 9 (compose healthcheck → /readyz): touches docker-compose.yml,
  outside the `src/` review scope the user invoked.
- Finding 10 (request_id ↔ trace_id correlation): touches the request-id
  contract and the existing `test_request_id_is_valid_uuid` test;
  intentional semantic change that deserves a deliberate pass.

## 2026-06-11 — test verification

Ran `python -m pytest tests/` in `src/dsv-app/` against the patched tree:
54 passed, 1 failed. Stashed and re-ran the failing test against the
pre-change tree: same failure. `test_routes.py::test_footer_content` is a
pre-existing breakage (footer template now reads `0.0.0` from the missing
VERSION.txt rather than the `v0.1...` the test expects). Not caused by my
edits.

