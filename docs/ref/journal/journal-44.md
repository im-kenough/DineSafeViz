# Journal 44

## 2026-05-09 — Review and update piv.md for accuracy

**Task:** Review `docs/how-to/operations/piv.md` against the current codebase
to ensure the Post Implementation Verification checklist reflects the app's
actual behavior.

### Findings

**Old piv.md checked:**
1. Grafana is NOT accessible at `localhost:3000` (expect: connection refused)
2. Proxy works at `localhost:5000/grafana/api/health` (expect: 200)
3. Dashboard page at `localhost:5000/dashboard` (expect: 200)
4. Home page has `href="/dashboard"`

**Problems found:**

1. **Grafana IS now exposed on port 3000.** `docker-compose.yml` maps port
   `3000:3000` for the `dsv-analytics` service (and the old `grafana` service).
   The admin panel is intentionally accessible at `localhost:3000/analytics/`.
   The old "connection refused" check was wrong.

2. **Proxy path changed from `/grafana/` to `/analytics/`.** `app.py` defines
   `analytics_proxy` at `/analytics/` (not `/grafana/`). Health check must be
   `localhost:5000/analytics/api/health`.

3. **New routes not covered:** `app.py` now has `/`, `/inspections`, `/info` in
   addition to `/dashboard`. PIV only checked `/dashboard`.

4. **Home page links changed.** `home.html` links to `/inspections`, `/dashboard`,
   and `/info` via `url_for`. The old grep for `href="/dashboard"` was too narrow.

### Decision

Updated piv.md to:
- Remove the incorrect "connection refused" check for port 3000
- Use `/analytics/api/health` for the proxy health check
- Add checks for all four app routes: `/`, `/inspections`, `/dashboard`, `/info`
- Verify home page navigation links to `/inspections` and `/dashboard`
- Add intro paragraph per docs-writer standard
