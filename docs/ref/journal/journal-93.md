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
