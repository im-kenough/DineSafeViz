# Journal 87

## 2026-06-10 — Session start

- Task: explain the Flask app in `src/dsv-app/app.py`, specifically how it
  serves the Grafana dashboard to unauthenticated users with an interactive
  date range.
- Read `src/dsv-app/app.py`, `templates/dashboard.html`, the
  `dsv-analytics/provisioning/` tree, and the relevant `dsv-analytics` and
  `dsv-analytics-permissions` blocks in `docker-compose.yml` to understand
  the end-to-end flow.

## 2026-06-11 — Phase 3 spec drafting

- Conversation expanded into Phase 3 scope: webapp v1.0 hardening for AKS
  and self-hosted observability stack on homelab Proxmox.
- Reviewed existing AKS design (`2026-06-09-aks-deployment-design.md`,
  722 lines) to mirror house structure and avoid re-deciding Phase 1
  things (ingress-nginx, cert-manager, AKV+CSI, GHA OIDC, CNPG, etc.).
- Wrote `docs/superpowers/specs/2026-06-11-phase3-design.md` covering
  Part 1 (webapp refactor) and Part 2 (homelab observability +
  Cloudflare Tunnel status page + Tailscale mesh + LGTM).
- Key decisions captured in spec:
  - Replace Flask reverse-proxy code with ingress-level routing.
  - ModSecurity v3 + OWASP CRS on ingress-nginx with Coraza
    fallback documented (ingress-nginx ModSec deprecation risk).
  - Two-VM homelab split: Observability (LGTM + Prometheus +
    Alertmanager) and Edge (Uptime Kuma + cloudflared).
  - Cloudflare Tunnel for public status page (no opened home ports);
    Tailscale for everything else (AKS↔home telemetry, admin access).
  - LGT + plain Prometheus; not Mimir at this scale.
  - OpenTelemetry-native instrumentation as the standard.
