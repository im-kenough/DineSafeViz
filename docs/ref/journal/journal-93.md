# Journal 93 — Code review fix batch

## 2026-06-11 00:00

### Summary
Applying 6 fixes from a final code review of DineSafeViz. All files read before editing.

### Files to edit
- `infra/ansible/roles/deploy/tasks/main.yml` — health check port 5000 → 8080
- `infra/ansible/roles/deploy/templates/env.j2` — fix port 5000 in root URL, add app user/password vars
- `infra/ansible/group_vars/all.yml` — add `app_analytics_db_app_user`
- `docker-compose.yml` — add healthcheck to dsv-app, update dsv-nginx depends_on
- `src/dsv-app/requirements.txt` — remove `opentelemetry-distro==0.63b1`
- `src/dsv-app/app.py` — add `_logger.propagate = False`

### Fix 1 — Ansible health check: port 5000 → 8080
- `tasks/main.yml` line 50: `url: "http://{{ app_vm_ip }}:5000/"` → port 8080
- `env.j2` line 17: `DSV_ANALYTICS_ROOT_URL=http://{{ app_vm_ip }}:5000/analytics/` → port 8080

### Fix 2 — env.j2 missing DSV_DB_APP_USER/PASSWORD
- Add after `DSV_DB_PASSWORD` line in env.j2
- Add `app_analytics_db_app_user: dinesafe_app` to group_vars/all.yml

### Fix 3 — nginx starts before gunicorn
- Add healthcheck block to dsv-app in docker-compose.yml
- Update dsv-nginx depends_on dsv-app to `condition: service_healthy`

### Fix 4 — Remove opentelemetry-distro from requirements.txt

### Fix 5 — Add _logger.propagate = False to app.py

### Fix 6 — Uninstall opentelemetry-distro from venv

---

## 2026-06-11 19:05 — Phase 3 Part 1 smoketest

Ran full smoketest of the Phase 3 Part 1 refactor after committing 6 code review
fix files and 5 docs files.

### Commits

- `511a2d0` — fix: code review fixes — ansible port 8080, db app creds in env.j2, nginx health dep, remove otel-distro, fix log propagation
- `fa16243` — docs: add journals 88-93 and phase3 part1 plan

### Build

`docker compose build --no-cache` succeeded. Both images built:
- `dsv-dsv-app:latest`
- `dsv-dsv-init-db:latest`

### Stack startup

`docker compose up -d` — all 6 containers started cleanly. `dsv-app` reported
`healthy` on the first health poll (attempt 1), meaning the gunicorn `/healthz`
probe passed immediately. `dsv-db` also healthy. `dsv-nginx` started after
`dsv-app` reached healthy state (condition: service_healthy).

### Smoke test results

| Test | Endpoint | Expected | Actual | Pass? |
|------|----------|----------|--------|-------|
| 3a | GET /healthz | 200 | 200, body=`ok` | PASS |
| 3b | GET /readyz | 200 | 200, body=`ok` | PASS |
| 3c | GET /metrics | dsv_* + flask_* lines | 40 dsv_ lines + flask_ lines | PASS |
| 3d | X-Request-ID header | UUID value | `f6208673-e426-47cd-944c-edc7d45d504b` | PASS |
| 3e | GET / | 200 | 200 | PASS |
| 3f | GET /analytics/ | 200 or 302 | 200 (Grafana served) | PASS |
| 3g | GET /info | 200 + HTML | 200 + full info page HTML | PASS |

`dsv_` metrics confirmed present: `dsv_db_query_duration_seconds`, `dsv_stats_cache_hits_total`.
`flask_http_request_duration_seconds` also present.
Note: `dsv_inspection_query` metric was not present in output — only home route had
been exercised so those buckets hadn't been created yet; not a failure.

### Structured JSON logs

Sample line from dsv-app:
```
{"asctime": "2026-06-11 19:03:34,502", "name": "dsv-app", "levelname": "INFO",
"message": "request", "request_id": "2350b2eb-69dc-419f-b251-aab0bfa762ae",
"route": "healthz", "method": "GET", "status": 200, "duration_ms": 0.05,
"remote_addr": "127.0.0.1", "user_agent": "Python-urllib/3.12"}
```
All required fields present: `request_id`, `route`, `method`, `status`. PASS.

Also present in logs: OTel console span JSON (multiline) for each request — this
is expected behaviour from the console span exporter. It's verbose but not a failure.

### nginx logs

Standard combined format, one line per proxied request. All test requests logged
correctly. No errors. PASS.

### Nonroot user check

```
uid=65532(nonroot) gid=65532(nonroot) groups=65532(nonroot)
```
PASS.

### Observations / concerns

1. OTel console span exporter produces verbose multiline JSON to stdout alongside
   structured log lines. In production, replace ConsoleSpanExporter with an OTLP
   exporter or remove it. Not a blocker for this phase.
2. `service.name` in OTel spans is `unknown_service` — should be set via
   `OTEL_SERVICE_NAME` env var in a future pass.
3. `dsv_inspection_query` metric bucket not populated at smoke test time because
   no `/inspections` route was hit — expected, not a bug.

### Tear down

`docker compose down` — clean shutdown, all containers and network removed.

### Verdict: PASS
