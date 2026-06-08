# Journal 62

## 2026-05-12 — Update arch-data.md from codebase

### 2026-05-12

- **Task:** Read the codebase and fill in all placeholder sections in
  `docs/ref/arch/arch-data.md` with accurate, code-derived content.
- **Files read:**
  - `src/dsv-db/init.sql` — single `inspections` table, 19 columns
  - `src/dsv-db/refresh.py` — seed vs. refresh logic, data sources,
    column mappings, sanitization (normalize fn, tab/CR/LF replacement)
  - `src/dsv-app/app.py` — Flask app, queries inspections by date range,
    groups by day, sorts by severity, reverse-proxies Grafana
  - `docker-compose.yml` — dsv-db (postgres:17.9), dsv-init-db (one-shot),
    dsv-app (Flask), dsv-analytics (Grafana 11.6)
  - `src/dsv-analytics/provisioning/` — datasource, dashboard config,
    dinesafe.json panel titles
  - `docs/ref/data.md` — existing data mapping doc with sample data and
    unified schema
  - `src/dsv-app/templates/index.html` — inspection table rendering
- **Action:** Rewrote `docs/ref/arch/arch-data.md` replacing all placeholder
  sections with code-accurate content.
