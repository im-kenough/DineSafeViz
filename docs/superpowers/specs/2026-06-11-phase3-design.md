# DineSafeViz Phase 3 — v1.0 Production Hardening + Self-Hosted Observability Design Spec

**Date:** June 11, 2026
**Purpose:** Take DineSafeViz from "running on AKS" (Phase 1) to a
defensible v1.0 production posture, and stand up a self-hosted observability
and status-reporting stack on the homelab Proxmox host. Phase 3 is split
into two parts that can ship independently.

## Summary

Phase 3 has two parts.

**Part 1 — Webapp v1.0 production refactor** removes the in-app reverse
proxy (responsibility shifts to ingress-nginx), separates database access
from a least-privilege application role, adds connection pooling via CNPG's
built-in PgBouncer, ships gunicorn in place of Flask's dev server, and
instruments the app for first-class operability: `/healthz`, `/readyz`,
`/metrics`, structured JSON logs, and per-request IDs. Container images
move to a non-root distroless base with a read-only root filesystem and
dropped Linux capabilities. Kubernetes manifests adopt PodSecurity
`restricted`, default-deny NetworkPolicies, resource requests/limits, a
PodDisruptionBudget, and topology spread across availability zones. The
ingress layer gains security response headers, rate limits, ModSecurity v3
running OWASP Core Rule Set, and (optionally) CrowdSec for behavioral
blocking. CI gains Trivy, gitleaks, bandit, semgrep, hadolint, tfsec, and
kubeconform as required checks, plus cosign keyless signing via the
existing GitHub Actions OIDC identity.

**Part 2 — Self-hosted observability + status page** stands up two Proxmox
VMs on the existing homelab (AMD Ryzen 7 5700G, 64 GB). The **Observability
VM** runs the LGT + Prometheus stack (Loki for logs, Grafana for UI, Tempo
for traces, Prometheus for metrics) plus Alertmanager and an Alertmanager-
to-Discord webhook bridge, all in a single Docker Compose file. The
**Edge VM** runs Uptime Kuma and `cloudflared`, exposing
`status.dinesafeviz.com` via a Cloudflare Tunnel — no inbound ports opened
on the home network. AKS clusters join a private Tailscale mesh and ship
telemetry to the Observability VM through an OpenTelemetry Collector
DaemonSet. Public-page probes traverse the open internet; internal probes
ride Tailscale. The Flask application emits OpenTelemetry traces and
metrics so the stack is vendor-neutral and forward-compatible with any
future managed observability backend.

## Goals

1. **Defensible v1.0 production posture** — every Phase 1 deferred concern
   (WAF, security headers, pod hardening, NetworkPolicy default-deny, image
   signing, CI security scanning) becomes a shipped artifact in Phase 3.
2. **Vendor-neutral observability** — the app emits OpenTelemetry; the
   backend (Loki + Tempo + Prometheus today) is replaceable without
   touching app code.
3. **Lean budget, with hardware leverage** — the homelab Proxmox host
   absorbs the entire observability + status-page workload at zero
   marginal cost. Cloud egress for telemetry stays under USD $5/month.
4. **No home-network exposure** — the public status page reaches Uptime
   Kuma via Cloudflare Tunnel; no port forwarding on the home router,
   no residential IP in DNS.
5. **Portfolio signal** — a hiring manager reading Phase 3 sees current
   industry practice: OpenTelemetry, Grafana LGTM stack, Cloudflare Tunnel
   + Tailscale role separation, ModSecurity v3 + OWASP CRS at the edge,
   keyless image signing, and pod-level security policies.
6. **Decoupled rollout** — Part 1 and Part 2 ship independently. Part 1
   makes the app safe to expose. Part 2 makes the app observable.

## Non-goals (Phase 3)

- 24/7 uptime SLA — the AKS stop-by-default lifecycle from Phase 1 stands.
- Multi-region active-active — remains a Phase 4 concern.
- Managed APM (Datadog, New Relic) — explicitly displaced by self-hosted.
- Service mesh (Istio, Linkerd) — Phase 4 if ever; mTLS via NetworkPolicy
  + Tailscale is sufficient at this scale.
- Continuous profiling (Pyroscope) — optional Phase 3 add-on if disk and
  RAM headroom on the Observability VM allow it.
- Kyverno or OPA Gatekeeper admission policies to verify cosign
  signatures in-cluster — signing in CI is the Phase 3 commitment;
  cluster-side verification is Phase 4.
- PR preview environments — remains a Phase 2 / Phase 4 item.

## Decision matrix

| Concern | Choice | Rationale |
|---|---|---|
| Reverse proxy responsibility | Ingress-nginx routes `/analytics/*` directly to the `dsv-analytics` Service; Flask `analytics_proxy()` deleted | Removes ~20 lines of app code; restores hop-by-hop header correctness to the proven nginx path |
| WAF engine | ModSecurity v3 inside ingress-nginx, OWASP CRS at paranoia level 1 | Free, declarative via annotations, widely understood; CRS is the de facto open WAF ruleset |
| WAF fallback path | Coraza WAF (Envoy filter or Caddy plugin) if ingress-nginx deprecates ModSec in the pinned chart version | Same SecLang rules transfer; documented branch decision |
| Behavioral defence layer (optional) | CrowdSec community blocklist + nginx bouncer | Free, complements signature-based WAF with IP reputation |
| App server | gunicorn with 4 workers, gthread worker class | Production-grade; Flask's built-in dev server is unsafe for production |
| Database connection pool | CNPG `Pooler` CR running PgBouncer in transaction mode | First-party CNPG feature; ~one YAML file; multiplexes app worker connections |
| Database privilege model | Two roles: `dinesafe_app` (CRUD on inspections, no DDL) and `dinesafe_migrator` (DDL) | Least privilege; blast-radius limit for SQLi or app RCE |
| Container base image | `gcr.io/distroless/python3-debian12:nonroot` | No shell, no package manager, smaller CVE surface, runs as UID 65532 |
| Pod security profile | PodSecurity `restricted` enforced at namespace level | Cluster-wide enforcement of non-root + dropped caps + seccomp |
| Network policy | Default-deny per namespace, explicit allows for each known dependency | Already a Phase 1 goal; Phase 3 materializes the manifests |
| Image signing | Cosign keyless signing via the existing GHA OIDC federated identity, with attestations published to Rekor | Free, modern provenance story; reuses Phase 1 identity plumbing |
| App instrumentation | OpenTelemetry SDK (traces + metrics + logs) | Vendor-neutral, current industry standard |
| Observability backend | Loki + Grafana + Tempo + Prometheus + Alertmanager (single Docker Compose, single VM) | Free, all Apache 2.0, all visualized in the same Grafana |
| Continuous profiling | Pyroscope (optional, Phase 3 stretch) | Adds flame graphs for slow-request analysis if headroom allows |
| Status page hosting | Uptime Kuma on a separate Edge VM, exposed via Cloudflare Tunnel | Public reachability without home network exposure; free DDoS at the edge |
| Private mesh transport | Tailscale (free Personal plan), with the Kubernetes Operator on AKS | Free, NAT-traversing, zero port forwarding, well-suited to homelab + cloud |
| Alert routing | Prometheus → Alertmanager → `alertmanager-discord` bridge → Discord webhook | Free; webhook bridge is a small Go container; Discord is the user's existing chat |
| Secondary alert channel | ntfy.sh (self-hosted) for `severity: critical` only | Free, push-to-phone, independent of Discord availability |
| Log retention | Hot 14 days, archived 90 days, deleted after 90 (Loki Index + filesystem chunks) | Matches portfolio-scale storage; documented ILM/ISM equivalent |
| Trace retention | 7 days in Tempo | Traces are large; 7 days covers all realistic incident-replay windows |
| Metric retention | 30 days in Prometheus, downsampled history out of scope | Sufficient for trend visualisation; Mimir would be overkill |
| Trust boundary | Public via Cloudflare only; everything else over Tailscale | Two tools, two roles, two failure domains |
| Homelab VM split | One Observability VM + one Edge VM | VM-level isolation as a virtual DMZ until physical VLAN DMZ exists |

## Decoupling Phase 3 from Phase 1 / Phase 2

| Phase 3 dependency | Where it comes from |
|---|---|
| Working AKS cluster, ingress-nginx, cert-manager, AKV + CSI | Phase 1 design spec (`2026-06-09-aks-deployment-design.md`) |
| ACR pull working via managed identity | Phase 1 |
| GitHub Actions OIDC federated identity | Phase 1 |
| CNPG operator + Cluster CR | Phase 1 |
| WAL archive + GRS basebackups | Phase 1 |
| Phase 2 DR cluster | Not required for Phase 3; future hook only |
| Phase 2 in-cluster monitoring | Explicitly replaced by Phase 3 Part 2 (self-hosted off-cluster) |

Phase 3 Part 1 is shippable the day Phase 1 is stable. Part 2 is shippable
the day Part 1 is stable; Part 1 produces the OpenTelemetry exports and
`/metrics` endpoint that Part 2 consumes.

---

# Part 1 — Webapp v1.0 production refactor

## Overview

The Phase 1 app runs Flask's development server inside a Debian-slim
container, with the application itself reverse-proxying `/analytics/*` to
the Grafana container. Phase 3 Part 1 closes the most visible gaps: app
server, container hardening, pod hardening, ingress hardening, database
least privilege, supply-chain scanning, and image signing. The result is
an application that can be exposed to the public internet under realistic
threat assumptions.

## Application code changes

### Remove the in-app reverse proxy

The `analytics_proxy` route and its `_HOP_BY_HOP` and `_analytics_session`
support code (`src/dsv-app/app.py:303-323`) are deleted. The
`templates/dashboard.html` iframe `src` is unchanged
(`/analytics/d/dinesafe/...`); ingress-nginx routes that path to the
`dsv-analytics` Service directly.

### Health endpoints

Two new routes, each cheap and independent:

| Route | Purpose | Behavior |
|---|---|---|
| `GET /healthz` | Liveness | Returns 200 unconditionally if the process responds. Wired to k8s `livenessProbe`. |
| `GET /readyz` | Readiness | Returns 200 only if `SELECT 1` against Postgres returns within 500ms. Wired to k8s `readinessProbe`. Pod removed from Service if DB is unreachable. |

The probes are deliberately separate so a slow database does not restart
otherwise-healthy app pods.

### Metrics endpoint

Adds `prometheus-flask-exporter` to `requirements.txt`. The exporter
automatically publishes:

- `flask_http_request_duration_seconds` histogram (per method + path + status)
- `flask_http_request_total` counter
- `flask_http_request_exceptions_total` counter
- `flask_http_request_in_progress` gauge

Custom metrics added in code:

| Metric | Type | Purpose |
|---|---|---|
| `dsv_db_query_duration_seconds` | Histogram | Per-query latency, labeled by route |
| `dsv_stats_cache_hits_total` | Counter | Effectiveness of the `_get_home_stats` cache |
| `dsv_stats_cache_misses_total` | Counter | Same |
| `dsv_inspection_rows_returned` | Histogram | Rows fetched per request, for capacity planning |

The `/metrics` endpoint is exposed on the same port as the app (Phase 3
Part 2's Prometheus scrapes it via Tailscale).

### Structured JSON logging

Replaces Flask's default text logging with `python-json-logger`. Every
log line is one JSON object: `timestamp`, `level`, `logger`, `message`,
`request_id`, `route`, `method`, `status`, `duration_ms`,
`remote_addr`, `user_agent`. Container Insights (Phase 1) and Loki
(Phase 3 Part 2) both ingest this format natively; no log parsing rules
required.

### Request IDs and trace context

A `@app.before_request` hook generates a UUIDv4 request ID and stores it
on Flask's `g`. Every log line includes it. The response header
`X-Request-ID` echoes it back so a user reporting an issue can quote the
ID for log lookup. Outbound calls (currently none, after the reverse-proxy
removal) would propagate the same ID. When OpenTelemetry instrumentation
lands, the `traceparent` header carries the same context across services.

### OpenTelemetry instrumentation

Phase 3 Part 1 adds the OTel SDK but defers the exporter wiring to Part 2
(no destination yet). Packages:

- `opentelemetry-distro[otlp]`
- `opentelemetry-instrumentation-flask`
- `opentelemetry-instrumentation-psycopg2`
- `opentelemetry-instrumentation-requests`

Auto-instrumentation produces spans for every request and every database
query without code changes. Service name and resource attributes set via
env vars (`OTEL_SERVICE_NAME=dsv-app`, `OTEL_RESOURCE_ATTRIBUTES`).
Exporter defaults to `console` in Phase 3 Part 1, switched to `otlp` in
Part 2.

### Database role split

The single `dinesafe` superuser role from Phase 1 splits into:

| Role | Privileges | Used by |
|---|---|---|
| `dinesafe_app` | `SELECT`, `INSERT`, `UPDATE` on `inspections` table; `USAGE` on schema; nothing else | Flask app via PgBouncer |
| `dinesafe_migrator` | DDL on the schema (CREATE/ALTER/DROP) | Migration Job run by a separate k8s Job, not the app pod |
| CNPG superuser | All | CNPG operator only; credentials owned and rotated by CNPG |

Passwords stay in CNPG-managed Kubernetes Secrets; the application
references them via the existing CSI mount pattern.

### Connection pooling via CNPG Pooler

A `Pooler` custom resource in transaction mode multiplexes incoming app
connections to a smaller upstream pool. Configuration:

| Setting | Value | Rationale |
|---|---|---|
| `type` | `rw` | App needs read-write |
| `pgbouncer.poolMode` | `transaction` | Best multiplexing for short-lived web queries |
| `pgbouncer.parameters.max_client_conn` | `200` | Generous for gunicorn × 4 workers × 4 threads |
| `pgbouncer.parameters.default_pool_size` | `25` | Per database, per user |
| `instances` | `1` Phase 3; `2` Phase 4 HA | Minimal footprint |

The app's `DSV_DB_HOST` env var points at the `Pooler`'s Service name
instead of the CNPG primary directly.

### gunicorn

Replaces Flask's development server. Configuration via `gunicorn.conf.py`:

| Setting | Value |
|---|---|
| `workers` | `4` (tunable; CPU × 2 + 1 is a reasonable starting heuristic) |
| `worker_class` | `gthread` |
| `threads` | `4` per worker |
| `timeout` | `30` |
| `graceful_timeout` | `30` |
| `keepalive` | `5` |
| `accesslog` | `-` (stdout, JSON via custom log class) |
| `errorlog` | `-` |
| `preload_app` | `True` (cheap shared memory before fork) |

The Dockerfile `CMD` becomes `["gunicorn", "-c", "gunicorn.conf.py", "app:app"]`.

## Container hardening

### Image

`gcr.io/distroless/python3-debian12:nonroot` as the runtime base. The
build stage uses `python:3.12-slim` to install dependencies, then copies
the site-packages tree into the distroless final stage. Resulting image
size: ~80 MB. No shell, no `apt`, no `bash`, no `sh`. Runs as UID 65532.

`USER nonroot:nonroot` is set explicitly in the final stage. The image
is built multi-arch (`linux/amd64`, `linux/arm64`) so it can run on
either AKS node SKU or local development on Apple Silicon.

### Dockerfile checklist

| Concern | Implementation |
|---|---|
| No build tooling in runtime image | Multi-stage build; only `site-packages` and the app are copied to the final stage |
| Pinned base image | `python:3.12-slim-bookworm@sha256:...` digest pin; renewed by Dependabot |
| `requirements.txt` integrity | `pip install --require-hashes` against a `requirements.lock.txt` produced by `pip-compile --generate-hashes` |
| Reproducible installs | `PIP_NO_CACHE_DIR=1`, `PYTHONDONTWRITEBYTECODE=1` |
| `HEALTHCHECK` | Omitted (Kubernetes probes own this) |

### Pod-level security context

Applied to every workload in the chart:

| Setting | Value |
|---|---|
| `runAsNonRoot` | `true` |
| `runAsUser` | `65532` |
| `runAsGroup` | `65532` |
| `fsGroup` | `65532` |
| `readOnlyRootFilesystem` | `true` |
| `allowPrivilegeEscalation` | `false` |
| `capabilities.drop` | `["ALL"]` |
| `seccompProfile.type` | `RuntimeDefault` |
| `emptyDir` volumes | Mounted at `/tmp` (for `tempfile`) and `/home/nonroot/.cache` |

## Kubernetes hardening

### PodSecurity admission

Each application namespace gets:

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

A pod that fails the `restricted` policy cannot start. This enforces
the container-hardening section above at the cluster level rather than
relying on every chart author to remember.

### NetworkPolicy

Default-deny per namespace plus explicit allows. Five policies total:

| Policy | Direction | From | To | Ports |
|---|---|---|---|---|
| `default-deny` | Both | All | All | None |
| `allow-dns` | Egress | All app pods | `kube-system` (kube-dns) | UDP 53, TCP 53 |
| `allow-app-to-pgbouncer` | Egress / Ingress | `dsv-app` | `pgbouncer-rw` Service | TCP 5432 |
| `allow-app-to-analytics` | Egress / Ingress | `dsv-app` (Grafana iframe path) | `dsv-analytics` | TCP 3000 |
| `allow-ingress-to-app` | Ingress | `ingress-nginx` namespace | `dsv-app` | TCP 8000 |
| `allow-otel-egress` | Egress | All app pods | Tailscale operator pod IP | TCP 4317 (OTLP) |

Cilium (Phase 1 choice) enforces; Hubble flow logs (Phase 2 or Phase 4)
provide observability for policy verification.

### Resource requests and limits

| Workload | CPU request | CPU limit | Memory request | Memory limit |
|---|---|---|---|---|
| `dsv-app` | `100m` | `500m` | `192Mi` | `512Mi` |
| `dsv-analytics` (Grafana) | `100m` | `500m` | `256Mi` | `512Mi` |
| `pgbouncer` (CNPG Pooler) | `50m` | `200m` | `64Mi` | `128Mi` |
| `dsv-db` (CNPG Postgres) | `200m` | `1000m` | `512Mi` | `1Gi` |

### PodDisruptionBudget

Each Deployment gets a PDB with `minAvailable: 1`. Node drains for AKS
patching cannot take the workload to zero replicas without manual
override. Once replicas climb to 2+ in Phase 4 this becomes non-trivial;
Phase 3 Part 1 keeps `replicas: 1` for cost reasons and notes the PDB
as forward-compatible.

### Topology spread

`topologySpreadConstraints` with `topologyKey: topology.kubernetes.io/zone`
and `maxSkew: 1` and `whenUnsatisfiable: ScheduleAnyway`. Honors the
three-zone node pool definition from Phase 1 without forcing the single
replica to a specific zone.

## Ingress hardening

### Security response headers

Applied via a single `ConfigMap` referenced by the ingress controller's
`add-headers` setting:

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=(), payment=()` |
| `Content-Security-Policy-Report-Only` (initial rollout) | `default-src 'self'; frame-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; report-uri /csp-report` |
| `Content-Security-Policy` (after one week of clean reports) | Same as above, drop `-Report-Only` |
| `server_tokens` (nginx config) | `off` |

The `frame-src 'self'` directive permits the Grafana iframe on
`dinesafeviz.com/dashboard` because Grafana is served from the same
origin under `/analytics/`.

### Rate limits

Annotations on the `Ingress` resource:

| Annotation | Value | Purpose |
|---|---|---|
| `nginx.ingress.kubernetes.io/limit-rps` | `20` | Per-IP requests per second |
| `nginx.ingress.kubernetes.io/limit-connections` | `10` | Per-IP concurrent connections |
| `nginx.ingress.kubernetes.io/proxy-body-size` | `1m` | No large uploads expected |
| `nginx.ingress.kubernetes.io/client-body-buffer-size` | `64k` | Mitigates slow-POST |

### ModSecurity + OWASP CRS

The ingress-nginx Helm values enable ModSecurity globally and mount the
CRS:

```yaml
controller:
  config:
    enable-modsecurity: "true"
    enable-owasp-modsecurity-crs: "true"
    modsecurity-snippet: |
      SecRuleEngine On
      SecAuditEngine RelevantOnly
      SecAuditLog /var/log/modsec_audit.log
      SecRequestBodyAccess On
      SecResponseBodyAccess Off
      Include /etc/nginx/owasp-modsecurity-crs/crs-setup.conf
      Include /etc/nginx/owasp-modsecurity-crs/rules/*.conf
```

Rollout sequence:

1. Enable in `DetectionOnly` mode for one week. Watch the audit log for
   false positives against legitimate traffic patterns (the DineSafe data
   visualization, Grafana iframe queries, etc.).
2. Document any required CRS exclusions in `infra/helm/ingress-values.yaml`.
3. Flip `SecRuleEngine` to `On` (blocking mode) after the exclusion set
   stabilizes.

<!-- prettier-ignore -->
> [!IMPORTANT]
> The ingress-nginx maintainers have signaled deprecation of the
> ModSecurity integration in newer controller versions. Before pinning the
> chart, verify ModSec is still supported in the chosen release. If
> unavailable, fall back to Coraza WAF as an Envoy filter
> (`coraza-proxy-wasm`) or migrate the WAF responsibility to an external
> tool. The CRS ruleset transfers unchanged.

### CrowdSec (optional behavioral layer)

If signature-based WAF is insufficient (repeated probing, distributed
credential stuffing, content scrapers), add CrowdSec as a complementary
layer:

| Component | Where it runs |
|---|---|
| CrowdSec agent | DaemonSet on AKS, reads ingress-nginx access logs |
| Local API (LAPI) | StatefulSet in the same namespace |
| `cs-firewall-bouncer` (nginx variant) | Sidecar on ingress-nginx, enforces blocks |
| Community blocklist | Pulled automatically from CrowdSec's hub |

Defer to Phase 3 Part 1 stretch if time permits; otherwise document as a
Phase 4 hook.

## Supply chain and CI security

### Required status checks on `main`

| Tool | Scope | Failure threshold |
|---|---|---|
| Trivy (image) | Container CVE scan of every built image | `HIGH` and `CRITICAL` block merge; `MEDIUM` warn-only |
| Trivy (IaC) | Terraform + Kubernetes manifests static analysis | `HIGH` and `CRITICAL` block |
| gitleaks | Secret detection in git history | Any finding blocks |
| bandit | Python security antipatterns | `HIGH` confidence blocks |
| semgrep (`p/security-audit`) | Cross-language SAST | `ERROR` blocks |
| hadolint | Dockerfile lints | `error` rules block |
| tfsec / checkov | Terraform best practices | `HIGH` blocks |
| kubeconform | Kubernetes manifest schema validation | Any failure blocks |
| `kube-score` | Manifest best practices (resources, probes, security context) | Configurable; warn-only initially |

All wired into the existing CI workflow that already runs `image-build.yml`.
Reports uploaded as GHA artifacts on every PR for review.

### Image signing with cosign

After image build, before push to ACR:

1. `cosign sign --yes <acr>/dsv-app:<tag>` using GHA's OIDC identity. The
   resulting signature is published to the Sigstore Rekor transparency
   log.
2. `cosign attest --yes --predicate sbom.json --type cyclonedx <acr>/...`
   to attach a CycloneDX SBOM produced by Syft.
3. Verification command documented in `docs/how-to/`: `cosign verify
   --certificate-identity-regexp '...' --certificate-oidc-issuer-regexp
   '...' <image>`.

In-cluster verification at admission (Sigstore Policy Controller or
Kyverno) is **deferred to Phase 4** to keep the Phase 3 scope tight.

## Implementation order (Part 1)

1. **App code changes** — health endpoints, `/metrics`, JSON logs, request
   IDs, OTel SDK (console exporter). Verify locally with the existing
   `docker compose up` flow.
2. **Database role split** — add `dinesafe_app` and `dinesafe_migrator`
   to the CNPG initdb SQL; update the Flask connection string to use the
   new role.
3. **CNPG Pooler** — apply the `Pooler` CR; update `DSV_DB_HOST` to point
   at the pooler service.
4. **gunicorn + Dockerfile rewrite** — multi-stage build, distroless
   final stage, non-root user. Verify local image runs.
5. **Helm chart hardening** — pod securityContext, PSA labels,
   NetworkPolicies, PDB, topology spread, resource requests/limits.
6. **Ingress hardening** — security headers ConfigMap, rate limits, route
   `/analytics/*` to the analytics Service (deleting the Flask proxy
   route depends on this landing first to avoid breaking the iframe).
7. **ModSecurity in DetectionOnly** — one week of audit log review.
8. **ModSecurity in blocking mode** — after exclusion list captured.
9. **CI scanners** — add each tool one PR at a time so the noise is
   tractable. Each landing PR includes the report from that scanner.
10. **Cosign signing + SBOM** — add to the image-build workflow.
11. **Documentation pass** — runbook entry for "verifying image
    signatures", "interpreting CSP report-uri output", "updating CRS
    exclusion list".

---

# Part 2 — Self-hosted observability and status reporting

## Overview

Phase 3 Part 2 stands up two Proxmox VMs and connects them to AKS via a
private Tailscale mesh. The Observability VM is the single source of
truth for logs, metrics, traces, and alerts; the Edge VM is the only
publicly reachable home asset and runs the status page through a
Cloudflare Tunnel. Telemetry flows AKS → Observability VM over Tailscale;
public status-page traffic flows Visitor → Cloudflare → tunnel → Edge VM.
The two paths do not share infrastructure.

## Topology

```
              ════════════════════ Public internet ════════════════════
                  │                                              │
                  │ dinesafeviz.com                              │ status.dinesafeviz.com
                  │ stg.dinesafeviz.com                          │
                  ▼                                              ▼
            ┌───────────────────┐                       ┌────────────────────┐
            │ Azure DNS +       │                       │ Cloudflare         │
            │ Static Public IP  │                       │ DDoS + TLS + WAF   │
            └────────┬──────────┘                       └─────────┬──────────┘
                     │                                            │
                     │                                            │ outbound-initiated
                     │                                            │ tunnel (no inbound
                     │                                            │ port at home)
        ════════════════════════════════════════════════════════════════════
                     │                                            │
                     ▼                                            ▼
            ┌───────────────────┐         ┌──────────────────────────────────┐
            │ AKS cluster       │         │ Proxmox host (Ryzen 7 5700G)     │
            │  • dsv-app (OTel) │         │                                  │
            │  • dsv-analytics  │         │ ┌──────────────────────────────┐ │
            │  • CNPG Postgres  │         │ │ Edge VM (4 GB, 2 vCPU)       │ │
            │  • OTel Collector │         │ │  • Uptime Kuma               │ │
            │    DaemonSet      │         │ │  • cloudflared               │ │
            │  • Tailscale K8s  │         │ │  • tailscale                 │ │
            │    Operator       │         │ │  NO inbound public ports     │ │
            └─────────┬─────────┘         │ └─────────────┬────────────────┘ │
                      │                   │               │                  │
                      │                   │ ┌─────────────▼────────────────┐ │
                      │                   │ │ Observability VM             │ │
                      │                   │ │ (24 GB, 6 vCPU)              │ │
                      └─────tailscale─────┼─▶ • grafana                   │ │
                            mesh          │ │  • loki                     │ │
                                          │ │  • tempo                    │ │
                                          │ │  • prometheus               │ │
                                          │ │  • alertmanager             │ │
                                          │ │  • otel-collector           │ │
                                          │ │  • alertmanager-discord     │ │
                                          │ │  • tailscale                │ │
                                          │ └──────────────────────────────┘ │
                                          └──────────────────────────────────┘
```

## Distinct traffic flows

The topology is easier to reason about as five independent flows. Each
uses exactly one of (Cloudflare Tunnel | Tailscale | public internet).

| # | Flow | Transport |
|---|---|---|
| 1 | Public visitor → status page | Cloudflare Tunnel |
| 2 | AKS app → Observability VM (telemetry push) | Tailscale |
| 3 | You → Grafana dashboards | Tailscale |
| 4 | Uptime Kuma → public app probe | Plain public internet (probes the actual outside path) |
| 5 | Uptime Kuma → internal service probes | Tailscale |

## Homelab VM design

### Observability VM

| Setting | Value |
|---|---|
| OS | Ubuntu Server 24.04 LTS |
| vCPU | 6 |
| RAM | 24 GB |
| Disk | 200 GB thin-provisioned (logs and traces grow; alert when 80% used) |
| Network | Internal Proxmox bridge; no public exposure ever |
| Tailscale | Yes, with subnet routes for the homelab LAN if needed |
| Backup | Proxmox snapshot daily; off-host backup weekly to external disk |

### Edge VM

| Setting | Value |
|---|---|
| OS | Ubuntu Server 24.04 LTS |
| vCPU | 2 |
| RAM | 4 GB |
| Disk | 20 GB |
| Network | Internal Proxmox bridge + Tailscale; `cloudflared` initiates outbound to Cloudflare |
| Tailscale | Yes, restricted ACL — can reach internal probe targets, not the Observability VM data planes |
| Backup | Proxmox snapshot weekly (Uptime Kuma's SQLite is the only stateful data) |

### Why two VMs

Three reasons drive the split:

1. **Blast radius**. A CVE in Uptime Kuma or `cloudflared` lands the
   attacker in a 4 GB VM with no access to log data, metrics history,
   or Grafana credentials.
2. **Public vs private exposure separation**. The Edge VM is the only
   home asset reachable from the public internet (via the tunnel). The
   property "only one VM is exposed" is provable and demonstrable.
3. **Future DMZ compatibility**. When a physical VLAN-isolated DMZ exists
   on the homelab network, the Edge VM moves to the DMZ VLAN unchanged;
   no application or networking rework needed.

## Observability VM Docker Compose

The full stack runs as one `docker-compose.yml`. Service overview:

| Service | Image | Port (host) | Mounts |
|---|---|---|---|
| `grafana` | `grafana/grafana-oss:11.x` | `3000` (tailnet-only) | `grafana-data:/var/lib/grafana`, provisioned dashboards from `./grafana/provisioning` |
| `loki` | `grafana/loki:3.x` | `3100` | `loki-data:/loki`, config from `./loki/loki-config.yaml` |
| `tempo` | `grafana/tempo:2.x` | `3200`, `4317`, `4318` (Tempo's own OTLP receivers, internal only) | `tempo-data:/var/tempo`, config from `./tempo/tempo-config.yaml` |
| `prometheus` | `prom/prometheus:v2.x` | `9090` | `prom-data:/prometheus`, config from `./prometheus/prometheus.yml` and `./prometheus/rules/` |
| `alertmanager` | `prom/alertmanager:v0.27.x` | `9093` | `am-data:/alertmanager`, config from `./alertmanager/alertmanager.yml` |
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.x` | `4317`, `4318` (OTLP from AKS) | Config from `./otelcol/config.yaml` |
| `alertmanager-discord` | `benjojo/alertmanager-discord:latest` | `9094` (internal) | None; reads webhook URL from env |
| `tailscale` (sidecar, optional) | `tailscale/tailscale:stable` | Host network | `tailscale-state:/var/lib/tailscale` |

All services bind to `127.0.0.1` or the Tailscale interface; none bind
to the host's external interface. Tailscale itself is installed on the
host OS (cleaner than the container sidecar) and provides routing.

### Storage plan

| Volume | Sized for | Retention strategy |
|---|---|---|
| `loki-data` | ~50 GB at observed log volume | Retention 90d via Loki `compactor` + filesystem retention; 14d "hot", 76d "cold" all on local disk |
| `tempo-data` | ~20 GB | 7 day retention; traces are large and rarely needed beyond a week |
| `prom-data` | ~10 GB | 30 day retention via `--storage.tsdb.retention.time=30d` |
| `grafana-data` | <1 GB | Dashboards mostly provisioned via files; this is just settings and saved queries |
| `am-data` | <100 MB | Alert silences and notification state |

Alert at 80% volume usage on each Loki and Tempo storage volume.

## Alerting

### Alertmanager → Discord bridge

Alertmanager's webhook receiver POSTs to the `alertmanager-discord`
container, which translates to Discord's embed format and POSTs to the
channel webhook URL (stored as `DISCORD_WEBHOOK` env var, mounted from a
Docker secret).

Routing tree:

```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: discord-default
  routes:
    - matchers: [severity="critical"]
      receiver: discord-critical-and-ntfy
      repeat_interval: 1h
    - matchers: [severity="info"]
      receiver: log-only
      repeat_interval: 24h
```

Inhibition rules pair coarse alerts to suppress noisier downstream ones
(for example: `KubeNodeNotReady` inhibits per-pod alerts on that node;
`PostgresDown` inhibits `DBQuerySlow`).

### Secondary push channel — ntfy.sh self-hosted

A `ntfy` container runs on the Observability VM, providing push to your
phone via the `ntfy` app. The `severity: critical` route also POSTs to a
private ntfy topic. ntfy is independent of Discord availability so a
critical Discord outage does not silently swallow alerts.

## Uptime Kuma probes

Probes defined on the Edge VM Uptime Kuma instance:

| Probe | Target | Interval | Where it runs from |
|---|---|---|---|
| HTTPS — public homepage | `https://dinesafeviz.com/` | 60s | Public internet (Edge VM → AKS Public IP) |
| HTTPS — public dashboard | `https://dinesafeviz.com/dashboard` | 60s | Public |
| HTTPS — staging | `https://stg.dinesafeviz.com/` | 5 min | Public |
| Keyword — homepage contains "DineSafe" | Same as above | 60s | Public |
| Cert expiry — `dinesafeviz.com` | TLS handshake | Daily | Public |
| Internal — Loki `/ready` | `http://loki.tailnet:3100/ready` | 60s | Tailscale |
| Internal — Tempo `/ready` | `http://tempo.tailnet:3200/ready` | 60s | Tailscale |
| Internal — Prometheus `/-/healthy` | `http://prometheus.tailnet:9090/-/healthy` | 60s | Tailscale |
| Internal — Grafana `/api/health` | `http://grafana.tailnet:3000/api/health` | 60s | Tailscale |
| Push — AKS heartbeat | An AKS CronJob POSTs to a Uptime Kuma push URL every 5 min | 5 min | Tailscale (CronJob → Edge VM) |

The push-based heartbeat from inside the cluster catches cases where the
public path is OK but in-cluster scheduling has stalled.

A public status page at `status.dinesafeviz.com` is published by Uptime
Kuma and reached via the Cloudflare Tunnel.

## Tailscale layout

### Identity and ACLs

Tailscale tailnet name: `dsv.ts.net` (default; rename optional).

| Node | Hostname | Role | ACL tags |
|---|---|---|---|
| Observability VM | `obs.dsv.ts.net` | Telemetry sink, Grafana host | `tag:obs` |
| Edge VM | `edge.dsv.ts.net` | Status page host, internal probe origin | `tag:edge` |
| AKS prod ingress (operator-exposed) | `aks-prod.dsv.ts.net` | AKS-side telemetry source | `tag:aks-prod` |
| AKS staging ingress (operator-exposed) | `aks-stg.dsv.ts.net` | AKS-side telemetry source | `tag:aks-stg` |
| Your laptop | `laptop` | Admin access | `tag:admin` |

ACL policy (Tailscale's HuJSON ACL file):

| Source | Destination | Ports |
|---|---|---|
| `tag:aks-prod`, `tag:aks-stg` | `tag:obs` | `4317`, `4318` (OTLP) |
| `tag:edge` | `tag:aks-prod`, `tag:aks-stg` | `80`, `443` (probes) |
| `tag:edge` | `tag:obs` | `3100`, `3200`, `9090`, `3000` (health endpoints only — restrict to `/ready`-style paths via Tailscale Serve if practical) |
| `tag:admin` | All | All |
| All else | All | Denied |

### AKS-side integration

The Tailscale Kubernetes Operator runs in the `tailscale` namespace on
each AKS cluster. The operator authenticates via a Tailscale OAuth client
whose credentials live in AKV and are mounted via the existing CSI
driver pattern from Phase 1.

The OTel Collector Service in AKS is annotated:

```yaml
metadata:
  annotations:
    tailscale.com/expose: "true"
    tailscale.com/hostname: "otelcol-aks-prod"
```

The Collector pod then has a stable Tailscale name (`otelcol-aks-prod.dsv.ts.net`),
which the AKS-side telemetry pipeline uses as its OTLP endpoint. From
the Observability VM's side, Prometheus scrapes `otelcol-aks-prod.dsv.ts.net:8888`
(Collector's own metrics endpoint) for cluster-internal metrics.

## Cloudflare Tunnel setup

### Tunnel and DNS

| Resource | Value |
|---|---|
| Cloudflare account | Free plan |
| Tunnel name | `dsv-status` |
| Tunnel credentials | Stored in 1Password / AKV; mounted into Edge VM at `/etc/cloudflared/credentials.json` |
| Tunnel hostname | `<uuid>.cfargotunnel.com` |
| Public hostname | `status.dinesafeviz.com` |
| DNS arrangement | Delegate `status.dinesafeviz.com` to Cloudflare DNS via NS record in Azure DNS; Cloudflare proxies (orange cloud) to the tunnel |
| Ingress rule | Route all hostname traffic to `http://localhost:3001` (Uptime Kuma's port on the Edge VM) |
| TLS | Cloudflare Universal SSL (free, automatic) — no cert management on the Edge VM |

### Cloudflare access policies (optional, free tier)

Cloudflare Access can gate the status page behind an email-OTP login if
you ever want it private. For a public portfolio status page, leave the
route open. Add an Access policy on `*.dinesafeviz.com` only if a
specific admin sub-path is later exposed.

## AKS-side OpenTelemetry Collector

A DaemonSet runs `otel/opentelemetry-collector-contrib` on each node.
Pipeline:

| Receiver | Processor | Exporter |
|---|---|---|
| `otlp` (gRPC + HTTP) from app pods | `batch`, `memory_limiter`, `resourcedetection` (Kubernetes attrs), `attributes` (drop noisy fields) | `otlphttp` to `obs.dsv.ts.net:4318` (Observability VM Collector) |
| `kubeletstats` (cAdvisor metrics) | Same | `prometheusremotewrite` to `prometheus.tailnet:9090/api/v1/write` |
| `k8s_events` | Same | `loki` exporter to Observability VM Loki |
| `filelog` (pod stdout) | `json_parser`, `attributes` | Same Loki sink |

The collector pod runs with a Tailscale sidecar (alternative to the
operator-exposed Service pattern) so the egress addresses resolve via
Tailscale MagicDNS.

Telemetry buffering: `file_storage` extension on the Collector retains up
to 1 GB on the AKS node's local disk for the case where the Tailscale
mesh or Observability VM is briefly unreachable.

## Flask OpenTelemetry instrumentation

`opentelemetry-distro` plus the Flask, psycopg2, and requests instrumentors
provide automatic spans. The `entrypoint` of the container becomes:

```
opentelemetry-instrument \
  --service_name dsv-app \
  --traces_exporter otlp \
  --metrics_exporter otlp \
  --logs_exporter otlp \
  --exporter_otlp_endpoint http://otelcol-aks-prod.tailscale:4318 \
  gunicorn -c gunicorn.conf.py app:app
```

Environment variables (sourced from a `ConfigMap`):

| Variable | Value |
|---|---|
| `OTEL_SERVICE_NAME` | `dsv-app` |
| `OTEL_RESOURCE_ATTRIBUTES` | `deployment.environment=prod,service.version=<git-sha>` |
| `OTEL_PROPAGATORS` | `tracecontext,baggage` |
| `OTEL_PYTHON_LOG_CORRELATION` | `true` (injects trace_id into log records) |
| `OTEL_METRIC_EXPORT_INTERVAL` | `30000` (30s) |

## Retention, cost, and capacity

### Storage

| Store | 30 days | 90 days | Cost driver |
|---|---|---|---|
| Loki | ~15 GB (compressed chunks) | ~45 GB | Local SSD on Observability VM |
| Tempo | ~20 GB | N/A (7-day retention) | Local SSD |
| Prometheus | ~5 GB | N/A (30-day retention) | Local SSD |

200 GB allocation gives ~6 months runway under observed homelab volume.

### Cloud egress (Azure → home)

| Source | Estimated daily volume | Monthly cost (Azure egress ~ $0.087/GB) |
|---|---|---|
| OTel Collector telemetry | 200–400 MB | $0.50–$1.00 |
| In-cluster cAdvisor / kubeletstats | 50–100 MB | $0.15–$0.30 |
| Pod log shipping (Loki) | 100–300 MB | $0.25–$0.80 |
| **Total** | | **$1–$2/month** |

Set conservative log levels in production (`INFO` and above) and ship
DEBUG only in staging. Monitor egress on the AKS-side Tailscale node
metrics monthly.

## Implementation order (Part 2)

1. **Provision two VMs in Proxmox** — Ubuntu 24.04, Tailscale installed
   on both, both joined to the tailnet. Verify Tailscale connectivity to
   your laptop.
2. **Stand up the Observability VM compose** — start with Grafana + Loki
   + Prometheus only. Point Prometheus at `localhost:9090` (itself) to
   prove the metric pipeline end-to-end before adding Tempo and OTel.
3. **Wire Cloudflare Tunnel on the Edge VM** — `cloudflared` daemon
   first, with a placeholder "hello world" backend, to confirm the tunnel
   works publicly before placing Uptime Kuma behind it.
4. **Add Uptime Kuma behind the tunnel** — public probes only (the
   dinesafeviz.com home page). Internal probes wait for the AKS-side
   Tailscale work.
5. **Add Tempo to the Observability VM compose** — verify trace storage
   with a synthetic OTLP push from `curl`.
6. **Add OTel Collector to the Observability VM compose** — config it
   to receive OTLP and fan out to Loki / Tempo / Prometheus.
7. **Install Tailscale K8s Operator on staging AKS** — verify
   operator-exposed Services resolve on the tailnet.
8. **Deploy OTel Collector DaemonSet on staging AKS** — pointing at the
   Observability VM. Confirm logs and traces appear in Grafana.
9. **Instrument Flask with OTel SDKs** — gunicorn entrypoint wraps with
   `opentelemetry-instrument`. Verify a `/inspections` request produces
   a trace with DB child spans.
10. **Provision Grafana dashboards** — at minimum: app golden signals,
    DB latency, AKS node health, Loki ingestion volume.
11. **Write Prometheus alerting rules + Alertmanager routing** — start
    with five rules (app down, DB down, 5xx rate, latency P99, disk
    usage). Tune routes and inhibitions over one week.
12. **Wire Discord and ntfy receivers** — verify alert paths end-to-end
    with a deliberate trigger.
13. **Migrate the prod AKS cluster** — same OTel + Tailscale layout as
    staging, after one week of staging stability.
14. **Promote internal Uptime Kuma probes** — once internal Tailscale
    endpoints are live.
15. **Document each piece as a runbook entry** in `docs/ref/arch/` and a
    how-to in `docs/how-to/`.

---

# Cross-cutting concerns

## Failure modes added in Phase 3

| Failure | Detection | Mitigation |
|---|---|---|
| Cloudflare Tunnel offline | Uptime Kuma push probe stops landing; Edge VM `cloudflared` logs | Restart `cloudflared`; tunnel re-authenticates automatically |
| Observability VM full disk | Grafana / Loki dashboards on `node_filesystem_free_bytes`; Prometheus alert at 80% | Manual retention reduction; promote disk in Proxmox |
| Tailscale auth key expired (AKS side) | OTel Collector pod logs `tailscale: not authenticated`; metrics scrape gap | Rotate via the OAuth client; document in runbook |
| ModSecurity blocks legitimate traffic | 403 spike in ingress access log; user reports | Add CRS exclusion in `infra/helm/ingress-values.yaml`; reload nginx |
| Cosign signing fails in CI | GHA workflow red | Re-run; Sigstore Fulkio/Rekor have occasional rough patches |
| Discord webhook revoked | Alerts emit but Discord shows nothing; ntfy still works for critical | Rotate webhook URL via Docker secret |
| Cloudflare account locked or rate-limited | Status page returns Cloudflare error pages | Document a fallback CNAME path; keep Tailscale Funnel config ready as a backup |
| ntfy push exhausted | Phone misses critical alerts | Self-hosted ntfy has no quota; monitor process health like any other |
| AKS-side OTel Collector buffer fills | Collector metrics emit `exporter_send_failed_log_records` | Increase `file_storage` quota; investigate Tailscale connectivity |

## Runbook entries to add to `docs/how-to/`

1. **Standing up the Observability VM from scratch** (Proxmox template
   to running stack).
2. **Rotating the Cloudflare Tunnel credentials.**
3. **Rotating the Tailscale OAuth client used by AKS.**
4. **Updating the OWASP CRS exclusion list.**
5. **Verifying a cosign signature on an image pulled from ACR.**
6. **Adding a new Uptime Kuma probe.**
7. **Restoring Loki / Tempo / Prometheus from snapshot.**
8. **Promoting a new Grafana dashboard via provisioning files.**

## Cost summary (Phase 3 incremental)

| Item | Monthly cost |
|---|---|
| Cloudflare free tier (tunnel, DNS, DDoS) | $0 |
| Tailscale Personal plan | $0 |
| Azure egress for telemetry (AKS → home) | ~$1–$2 |
| Proxmox VMs (existing hardware) | $0 marginal |
| ntfy.sh self-hosted | $0 |
| LGT + Prometheus + Alertmanager (containers) | $0 |
| Cosign + Rekor (Sigstore) | $0 |
| Trivy, gitleaks, bandit, semgrep, hadolint, tfsec, kubeconform | $0 (OSS, runs in GHA) |
| **Phase 3 monthly delta** | **~$1–$2** |

## Roadmap (Phase 4 hooks)

1. Sigstore Policy Controller for cluster-side cosign signature
   verification at admission.
2. Pyroscope continuous profiling on the Observability VM.
3. Hubble flow logs for NetworkPolicy verification.
4. SLO definitions + Grafana SLO panels driven by `slo-generator`.
5. Replicas ≥ 2 for `dsv-app` with the PDB enforcing real availability
   (requires Redis or another shared cache to retire the in-process
   `_get_home_stats` cache).
6. CrowdSec promoted from optional Phase 3 layer to default.
7. PR preview environments using a wildcard cert + dynamic ingress.
8. Storage VM (TrueNAS) for off-host backups of Observability VM and
   AKS WAL archives mirrored from Azure.
9. Network DMZ VLAN on the homelab side; Edge VM moves there.

## Open questions / deferred decisions

1. **ModSecurity in ingress-nginx**: pin a chart version that still ships
   ModSec, or plan migration to Coraza-on-Envoy at the time of writing.
   Decide before Part 1 implementation step 7.
2. **Pyroscope inclusion in Part 2**: defer to stretch goal; revisit
   when Observability VM has been live one month with stable headroom.
3. **Move `dinesafeviz.com` DNS to Cloudflare entirely vs. delegating
   only `status.dinesafeviz.com`**: keeping Azure DNS for the apex is
   the simpler change; revisit if Cloudflare proxy features for the
   apex domain become valuable.
4. **CrowdSec vs. ModSecurity-only**: start with CRS; add CrowdSec only
   if real attack telemetry justifies it.
5. **Single-VM vs. two-VM homelab layout**: this spec commits to
   two-VM; the only reason to collapse would be Proxmox resource
   pressure that does not exist today.

## References

- Phase 1 design: [`2026-06-09-aks-deployment-design.md`](./2026-06-09-aks-deployment-design.md)
- OWASP Core Rule Set: <https://coreruleset.org/>
- OpenTelemetry Python: <https://opentelemetry.io/docs/languages/python/>
- Grafana LGTM stack overview: <https://grafana.com/docs/>
- Cloudflare Tunnel: <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>
- Tailscale Kubernetes Operator: <https://tailscale.com/kb/1236/kubernetes-operator>
- CNPG `Pooler` (PgBouncer): <https://cloudnative-pg.io/documentation/current/connection_pooling/>
- Sigstore cosign keyless signing: <https://docs.sigstore.dev/cosign/signing/overview/>
- Distroless images: <https://github.com/GoogleContainerTools/distroless>
- Alertmanager Discord bridge: <https://github.com/benjojo/alertmanager-discord>
