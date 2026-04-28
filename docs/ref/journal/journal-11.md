# Journal 11 — Grafana Admin Access

## 2026-04-27 — Session start

Refactoring Grafana config to allow admin login directly on port 3000, while keeping the anonymous viewer embed via Flask proxy intact.

Design decisions:
- Expose port 3000 for direct admin access
- Re-enable login form (was explicitly disabled)
- Admin credentials sourced from .env via GF_ADMIN_USER / GF_ADMIN_PASSWORD
- allowUiUpdates: true on dashboard provider so provisioned dashboard is editable in UI (ephemeral — export JSON to persist)
- datasource made editable: true so admin can tweak it from the UI
- Create .env.example to document required vars

## 2026-04-27 — Implementation

Editing: docker-compose.yml, dashboard.yml, datasource.yml, creating .env.example
