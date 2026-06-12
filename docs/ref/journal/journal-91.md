# Journal 91

## 2026-06-11 — Task 7: nginx routing + analytics proxy removal

### Context
Tasks 1–6 complete. HEAD at 1d9723e. Implementing Task 7: replace Flask
analytics reverse proxy with an nginx container.

### Plan
1. Create `src/dsv-nginx/nginx.conf`
2. Replace `docker-compose.yml` (add dsv-nginx service, remove dsv-app ports,
   update Grafana root URL to use port 8080)
3. Remove `import requests as http_requests` from `app.py` (line 15)
4. Remove proxy globals and `analytics_proxy()` route from `app.py` (lines 392-412)
5. Remove `requests==2.34.2` from `requirements.txt`
6. Delete `src/dsv-app/tests/test_proxy.py`
7. Run tests to confirm no regressions
8. Commit

### 2026-06-11 — Step 1: Create src/dsv-nginx/nginx.conf
Created directory and nginx.conf with upstream proxy rules:
- `/analytics/` → `dsv-analytics:3000`
- `/` → `dsv-app:8000`

### 2026-06-11 — Step 2: Replace docker-compose.yml
Added `dsv-nginx` service (nginx:stable-alpine, port 8080:80).
Removed `dsv-app` external port mapping (was 5000:5000).
Updated `GF_SERVER_ROOT_URL` default from `localhost:5000` to `localhost:8080`.

### 2026-06-11 — Step 3+4: Remove analytics proxy from app.py
Removed `import requests as http_requests` and the three proxy globals
plus `analytics_proxy()` route function.

### 2026-06-11 — Step 5: Remove requests from requirements.txt
Removed `requests==2.34.2` line.

### 2026-06-11 — Step 6: Delete test_proxy.py
Deleted `src/dsv-app/tests/test_proxy.py` (tests analytics_proxy which no longer exists).
