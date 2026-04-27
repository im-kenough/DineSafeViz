# Grafana Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Grafana dashboard with 11 panels visualizing DineSafe inspection data, embedded in the Flask app via iframe and proxied through Flask.

**Architecture:** Grafana runs as an internal-only Docker service (no published ports). Flask proxies `/grafana/*` to it using the `requests` library. A `/dashboard` route renders an iframe in kiosk mode. All Grafana config (datasource, dashboard JSON) is provisioned as code from `src/grafana/provisioning/`.

**Tech Stack:** Grafana 11.6.0, PostgreSQL (existing), Flask (existing), `requests` library

---

## File Structure

```
src/grafana/provisioning/
  datasources/
    datasource.yml            # PostgreSQL datasource config (env var interpolation)
  dashboards/
    dashboard.yml             # File-based provider pointing at this directory
    dinesafe.json             # 11-panel dashboard definition

src/web/
  app.py                      # Modified: add /dashboard route + /grafana proxy
  requirements.txt            # Modified: add requests
  templates/
    index.html                # Modified: add Dashboard nav link
    dashboard.html            # New: iframe page

docker-compose.yml            # Modified: add grafana service
```

---

### Task 1: Grafana Provisioning Files

**Files:**
- Create: `src/grafana/provisioning/datasources/datasource.yml`
- Create: `src/grafana/provisioning/dashboards/dashboard.yml`

These two small YAML files tell Grafana where to find its database and dashboards on startup.

- [ ] **Step 1: Create datasource config**

Create `src/grafana/provisioning/datasources/datasource.yml`:

```yaml
apiVersion: 1

datasources:
  - name: PostgreSQL
    type: grafana-postgresql-datasource
    access: proxy
    url: ${DB_HOST}:${DB_PORT}
    database: ${DB_NAME}
    user: ${DB_USER}
    secureJsonData:
      password: ${DB_PASSWORD}
    jsonData:
      sslmode: disable
      postgresVersion: 1700
    isDefault: true
    editable: false
```

- [ ] **Step 2: Create dashboard provider config**

Create `src/grafana/provisioning/dashboards/dashboard.yml`:

```yaml
apiVersion: 1

providers:
  - name: DineSafe
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: false
```

- [ ] **Step 3: Commit**

```bash
git add src/grafana/provisioning/datasources/datasource.yml src/grafana/provisioning/dashboards/dashboard.yml
git commit -m "feat(grafana): add datasource and dashboard provider configs"
```

---

### Task 2: Grafana Dashboard JSON

**Files:**
- Create: `src/grafana/provisioning/dashboards/dinesafe.json`

This is the large dashboard-as-code file. 11 panels, all using raw SQL against the PostgreSQL datasource. The dashboard UID is `dinesafe` (referenced by the iframe URL later).

- [ ] **Step 1: Create the dashboard JSON**

Create `src/grafana/provisioning/dashboards/dinesafe.json` with this content. The file is long but mechanical — each panel follows the same structure with a different SQL query and visualization type.

```json
{
  "uid": "dinesafe",
  "title": "DineSafe Inspections",
  "timezone": "browser",
  "schemaVersion": 39,
  "version": 1,
  "editable": false,
  "panels": [
    {
      "id": 1,
      "title": "Total Inspections",
      "type": "stat",
      "gridPos": { "h": 4, "w": 8, "x": 0, "y": 0 },
      "targets": [
        {
          "rawSql": "SELECT COUNT(*) AS \"Total\" FROM inspections;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "thresholds": { "steps": [{ "color": "#4a7aff", "value": null }] }
        },
        "overrides": []
      },
      "options": {
        "colorMode": "value",
        "graphMode": "none",
        "reduceOptions": { "calcs": ["lastNotNull"] }
      }
    },
    {
      "id": 2,
      "title": "Crucial Infractions",
      "type": "stat",
      "gridPos": { "h": 4, "w": 8, "x": 8, "y": 0 },
      "targets": [
        {
          "rawSql": "SELECT COUNT(*) AS \"Crucial\" FROM inspections WHERE severity = 'C - Crucial';",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "thresholds": { "steps": [{ "color": "#dc2626", "value": null }] }
        },
        "overrides": []
      },
      "options": {
        "colorMode": "value",
        "graphMode": "none",
        "reduceOptions": { "calcs": ["lastNotNull"] }
      }
    },
    {
      "id": 3,
      "title": "Total Fines Collected",
      "type": "stat",
      "gridPos": { "h": 4, "w": 8, "x": 16, "y": 0 },
      "targets": [
        {
          "rawSql": "SELECT COALESCE(SUM(amount_fined::numeric), 0) AS \"Fines\" FROM inspections WHERE amount_fined IS NOT NULL AND amount_fined != '';",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD",
          "thresholds": { "steps": [{ "color": "#ca8a04", "value": null }] }
        },
        "overrides": []
      },
      "options": {
        "colorMode": "value",
        "graphMode": "none",
        "reduceOptions": { "calcs": ["lastNotNull"] }
      }
    },
    {
      "id": 4,
      "title": "Inspections Over Time",
      "type": "timeseries",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 4 },
      "targets": [
        {
          "rawSql": "SELECT date_trunc('week', inspection_date) AS \"time\", COUNT(*) AS \"Inspections\" FROM inspections WHERE inspection_date IS NOT NULL GROUP BY 1 ORDER BY 1;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": { "fillOpacity": 10, "lineWidth": 2 }
        },
        "overrides": []
      },
      "options": {
        "tooltip": { "mode": "single" },
        "legend": { "displayMode": "list", "placement": "bottom" }
      }
    },
    {
      "id": 5,
      "title": "Fines Issued Over Time",
      "type": "barchart",
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 4 },
      "targets": [
        {
          "rawSql": "SELECT date_trunc('month', inspection_date) AS \"time\", SUM(amount_fined::numeric) AS \"Fines\" FROM inspections WHERE amount_fined IS NOT NULL AND amount_fined != '' AND inspection_date IS NOT NULL GROUP BY 1 ORDER BY 1;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD",
          "color": { "mode": "fixed", "fixedColor": "#ca8a04" }
        },
        "overrides": []
      },
      "options": {
        "tooltip": { "mode": "single" },
        "legend": { "displayMode": "list", "placement": "bottom" }
      }
    },
    {
      "id": 6,
      "title": "Severity Breakdown",
      "type": "piechart",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 12 },
      "targets": [
        {
          "rawSql": "SELECT COALESCE(severity, 'None') AS \"Severity\", COUNT(*) AS \"Count\" FROM inspections GROUP BY 1 ORDER BY 2 DESC;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": { "defaults": {}, "overrides": [] },
      "options": {
        "legend": { "displayMode": "table", "placement": "right", "values": ["value", "percent"] },
        "pieType": "donut",
        "tooltip": { "mode": "single" }
      }
    },
    {
      "id": 7,
      "title": "Outcome Distribution",
      "type": "piechart",
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 12 },
      "targets": [
        {
          "rawSql": "SELECT COALESCE(outcome, 'None') AS \"Outcome\", COUNT(*) AS \"Count\" FROM inspections WHERE outcome IS NOT NULL AND outcome != 'None' GROUP BY 1 ORDER BY 2 DESC;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": { "defaults": {}, "overrides": [] },
      "options": {
        "legend": { "displayMode": "table", "placement": "right", "values": ["value", "percent"] },
        "pieType": "donut",
        "tooltip": { "mode": "single" }
      }
    },
    {
      "id": 8,
      "title": "Top 10 Most-Inspected Establishments",
      "type": "barchart",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 20 },
      "targets": [
        {
          "rawSql": "SELECT establishment_name AS \"Establishment\", COUNT(*) AS \"Inspections\" FROM inspections WHERE establishment_name IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": { "mode": "fixed", "fixedColor": "#4a7aff" }
        },
        "overrides": []
      },
      "options": {
        "orientation": "horizontal",
        "tooltip": { "mode": "single" },
        "legend": { "displayMode": "list", "placement": "bottom" }
      }
    },
    {
      "id": 9,
      "title": "Actions Taken Over Time",
      "type": "timeseries",
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 20 },
      "targets": [
        {
          "rawSql": "SELECT date_trunc('month', inspection_date) AS \"time\", action AS \"Action\", COUNT(*) AS \"Count\" FROM inspections WHERE action IS NOT NULL AND action != 'None' AND inspection_date IS NOT NULL GROUP BY 1, 2 ORDER BY 1;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": { "fillOpacity": 50, "stacking": { "mode": "normal" }, "lineWidth": 1 }
        },
        "overrides": []
      },
      "options": {
        "tooltip": { "mode": "multi" },
        "legend": { "displayMode": "list", "placement": "bottom" }
      },
      "transformations": [
        {
          "id": "prepareTimeSeries",
          "options": { "format": "multi" }
        }
      ]
    },
    {
      "id": 10,
      "title": "Crucial Infractions by Establishment Type",
      "type": "barchart",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 28 },
      "targets": [
        {
          "rawSql": "SELECT establishment_type AS \"Type\", COUNT(*) AS \"Crucial\" FROM inspections WHERE severity = 'C - Crucial' AND establishment_type IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10;",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": { "mode": "fixed", "fixedColor": "#dc2626" }
        },
        "overrides": []
      },
      "options": {
        "orientation": "horizontal",
        "tooltip": { "mode": "single" },
        "legend": { "displayMode": "list", "placement": "bottom" }
      }
    },
    {
      "id": 11,
      "title": "Inspections by Day of Week",
      "type": "barchart",
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 28 },
      "targets": [
        {
          "rawSql": "SELECT CASE EXTRACT(dow FROM inspection_date) WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue' WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri' WHEN 6 THEN 'Sat' END AS \"Day\", COUNT(*) AS \"Inspections\" FROM inspections WHERE inspection_date IS NOT NULL GROUP BY EXTRACT(dow FROM inspection_date), 1 ORDER BY EXTRACT(dow FROM inspection_date);",
          "format": "table",
          "datasource": { "type": "grafana-postgresql-datasource", "uid": "" },
          "refId": "A"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": { "mode": "fixed", "fixedColor": "#4a7aff" }
        },
        "overrides": []
      },
      "options": {
        "tooltip": { "mode": "single" },
        "legend": { "displayMode": "list", "placement": "bottom" }
      }
    }
  ],
  "time": { "from": "2023-11-01T00:00:00.000Z", "to": "now" },
  "refresh": "",
  "templating": { "list": [] },
  "annotations": { "list": [] }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/grafana/provisioning/dashboards/dinesafe.json
git commit -m "feat(grafana): add 11-panel dashboard definition"
```

---

### Task 3: Add Grafana Service to Docker Compose

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add grafana service**

Add the following service to `docker-compose.yml`, after the `web` service and before `volumes`:

```yaml
  grafana:
    image: grafana/grafana:11.6.0
    environment:
      GF_SERVER_ROOT_URL: /grafana/
      GF_SERVER_SERVE_FROM_SUB_PATH: "true"
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
      GF_AUTH_DISABLE_LOGIN_FORM: "true"
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /etc/grafana/provisioning/dashboards/dinesafe.json
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./src/grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      db:
        condition: service_healthy
```

No `ports:` section — Grafana is internal-only.

- [ ] **Step 2: Add grafana dependency to web service**

In the `web` service's `depends_on`, add `grafana` so Flask doesn't start proxying before Grafana is up:

```yaml
    depends_on:
      db:
        condition: service_healthy
      grafana:
        condition: service_started
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(docker): add internal-only Grafana service"
```

---

### Task 4: Add `requests` Dependency

**Files:**
- Modify: `src/web/requirements.txt`

- [ ] **Step 1: Add requests to requirements.txt**

Add `requests` to `src/web/requirements.txt`. The file should become:

```
flask==3.1.3
psycopg2-binary==2.9.12
requests==2.32.3
```

- [ ] **Step 2: Commit**

```bash
git add src/web/requirements.txt
git commit -m "build: add requests dependency for Grafana proxy"
```

---

### Task 5: Flask Proxy Route

**Files:**
- Modify: `src/web/app.py` (add ~25 lines)
- Create: `src/web/tests/test_proxy.py`

This task adds the `/grafana/<path>` catch-all route that forwards requests to the internal Grafana container.

- [ ] **Step 1: Write failing test for proxy route**

Create `src/web/tests/test_proxy.py`:

```python
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module


def _mock_grafana_response(status_code=200, content=b"grafana html",
                           headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = headers or {"Content-Type": "text/html"}
    return resp


def test_grafana_proxy_forwards_get():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    mock_resp = _mock_grafana_response()
    with patch("app.http_requests.request", return_value=mock_resp) as mock_req:
        resp = client.get("/grafana/d/dinesafe/dinesafe-inspections")
    mock_req.assert_called_once()
    call_args = mock_req.call_args
    assert call_args[0][0] == "GET"
    assert "grafana:3000/grafana/d/dinesafe/dinesafe-inspections" in call_args[0][1]
    assert resp.status_code == 200
    assert resp.data == b"grafana html"


def test_grafana_proxy_passes_query_string():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    mock_resp = _mock_grafana_response()
    with patch("app.http_requests.request", return_value=mock_resp) as mock_req:
        resp = client.get("/grafana/d/dinesafe/x?kiosk&orgId=1")
    url = mock_req.call_args[0][1]
    assert "kiosk" in url
    assert "orgId=1" in url


def test_grafana_proxy_returns_grafana_status_code():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    mock_resp = _mock_grafana_response(status_code=404, content=b"not found")
    with patch("app.http_requests.request", return_value=mock_resp):
        resp = client.get("/grafana/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/web && python -m pytest tests/test_proxy.py -v`
Expected: FAIL — `app` module has no `requests` attribute and no `/grafana` route.

- [ ] **Step 3: Implement the proxy route**

Add to the top of `src/web/app.py`, after the existing imports:

```python
import requests as http_requests
```

Add at the bottom of `src/web/app.py`, after the `index()` route:

```python
GRAFANA_URL = "http://grafana:3000"


@app.route("/grafana/", defaults={"path": ""})
@app.route("/grafana/<path:path>")
def grafana_proxy(path):
    """Reverse-proxy requests to the internal Grafana container."""
    url = f"{GRAFANA_URL}/grafana/{path}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    resp = http_requests.request(
        method=request.method,
        url=url,
        headers={k: v for k, v in request.headers if k.lower() != "host"},
        data=request.get_data(),
        allow_redirects=False,
    )
    excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
    return resp.content, resp.status_code, headers
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src/web && python -m pytest tests/test_proxy.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run all existing tests to check for regressions**

Run: `cd src/web && python -m pytest tests/ -v`
Expected: All tests pass (existing + new).

- [ ] **Step 6: Commit**

```bash
git add src/web/app.py src/web/tests/test_proxy.py
git commit -m "feat: add Flask reverse proxy for internal Grafana"
```

---

### Task 6: Dashboard Route and Template

**Files:**
- Modify: `src/web/app.py` (add ~8 lines)
- Create: `src/web/templates/dashboard.html`
- Create: `src/web/tests/test_dashboard.py`

- [ ] **Step 1: Write failing test for /dashboard route**

Create `src/web/tests/test_dashboard.py`:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module


def test_dashboard_returns_200():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_dashboard_contains_iframe():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    resp = client.get("/dashboard")
    assert b"<iframe" in resp.data
    assert b"/grafana/d/dinesafe" in resp.data
    assert b"kiosk" in resp.data


def test_dashboard_has_home_link():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    resp = client.get("/dashboard")
    assert b'href="/"' in resp.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/web && python -m pytest tests/test_dashboard.py -v`
Expected: FAIL — no `/dashboard` route, no template.

- [ ] **Step 3: Create dashboard template**

Create `src/web/templates/dashboard.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DineSafeViz — Dashboard</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <style>
        .dashboard-frame {
            width: 100%;
            height: calc(100vh - 120px);
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface);
        }
    </style>
</head>
<body>
    <h1>DineSafe Dashboard</h1>
    <div class="tabs">
        <a href="/">Inspections</a>
        <a href="/dashboard" class="active">Dashboard</a>
    </div>
    <iframe class="dashboard-frame"
            src="/grafana/d/dinesafe/dinesafe-inspections?kiosk"
            frameborder="0"></iframe>
</body>
</html>
```

- [ ] **Step 4: Add the dashboard route to app.py**

Add to `src/web/app.py`, between the `index()` route and `GRAFANA_URL`:

```python
@app.route("/dashboard")
def dashboard():
    """Render the Grafana dashboard iframe page."""
    return render_template("dashboard.html")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd src/web && python -m pytest tests/test_dashboard.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/web/app.py src/web/templates/dashboard.html src/web/tests/test_dashboard.py
git commit -m "feat: add /dashboard route with Grafana iframe"
```

---

### Task 7: Add Dashboard Nav Link to Home Page

**Files:**
- Modify: `src/web/templates/index.html`
- Modify: `src/web/tests/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to the bottom of `src/web/tests/test_routes.py`:

```python
def test_home_has_dashboard_link():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/dashboard"' in resp.data
    assert b"Dashboard" in resp.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/web && python -m pytest tests/test_routes.py::test_home_has_dashboard_link -v`
Expected: FAIL — no dashboard link in index.html yet.

- [ ] **Step 3: Add nav link to index.html**

In `src/web/templates/index.html`, replace:

```html
    <h1>DineSafe Inspections</h1>
```

with:

```html
    <h1>DineSafe Inspections</h1>

    <div class="tabs">
        <a href="/" class="active">Inspections</a>
        <a href="/dashboard">Dashboard</a>
    </div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/web && python -m pytest tests/test_routes.py::test_home_has_dashboard_link -v`
Expected: PASS.

- [ ] **Step 5: Run all tests**

Run: `cd src/web && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/web/templates/index.html src/web/tests/test_routes.py
git commit -m "feat: add Dashboard nav link to home page"
```

---

### Task 8: Integration Smoke Test

**Files:** None new — this task validates the full stack.

- [ ] **Step 1: Start the stack**

```bash
docker compose up --build -d
```

- [ ] **Step 2: Verify Grafana is not externally accessible**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Expected: Connection refused or empty reply (Grafana has no published port).

- [ ] **Step 3: Verify proxy works**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/grafana/api/health
```

Expected: `200` — Grafana's health endpoint is reachable through the proxy.

- [ ] **Step 4: Verify dashboard page loads**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/dashboard
```

Expected: `200`.

- [ ] **Step 5: Verify home page has dashboard link**

```bash
curl -s http://localhost:5000/ | grep -o 'href="/dashboard"'
```

Expected: `href="/dashboard"`.

- [ ] **Step 6: Verify dashboard iframe loads Grafana content**

```bash
curl -s http://localhost:5000/grafana/d/dinesafe/dinesafe-inspections?kiosk | head -5
```

Expected: HTML content from Grafana (should contain `<html` or `grafana`).

- [ ] **Step 7: Tear down**

```bash
docker compose down
```

- [ ] **Step 8: Commit (if any fixes were needed)**

Only if changes were made during smoke testing. If everything passed clean, no commit needed.
