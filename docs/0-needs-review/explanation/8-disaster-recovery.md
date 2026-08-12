# Disaster recovery and resiliency

> [!NOTE]
> **Target state (v0.4.0, in progress).** This document describes the planned
> Azure/AKS architecture, not the currently deployed Proxmox environment. For
> the live deployment, see the [Proxmox install guide](../how-to/1-install/README.md).

## Scenario

### City of Toronto Open Data portal is unavailable

TODO: https://github.com/im-kenough/DineSafeViz/issues/62


### AKS backup and recovery

TODO: https://learn.microsoft.com/en-us/azure/architecture/operator-guides/aks/aks-backup-and-recovery

## Cost-aware availability: the holding-page cutover

AKS is not free, and running it 24/7 for an intermittent portfolio demo is
wasteful. The plan is to run the cluster only when it is needed — demos,
filming, DR drills — and to serve a static **holding page** from
`dinesafeviz.com` the rest of the time. The holding page links to the repo
and, later, a recorded walkthrough, so the project stays presentable while the
cluster is parked.

This is the same cutover muscle as the regional DR runbook described later
(a manual `workflow_dispatch` plus a DNS-layer swap), applied to a cheaper
and more frequent event: intentionally parking a *healthy* demo to stop
paying for idle compute.

### Options considered

| Option | Standing cost | Trigger | Verdict |
|---|---|---|---|
| Azure Front Door Standard | ~$35/mo base, always on | health probe (auto) | **Rejected.** The base fee bills even while AKS is scaled to zero — it defeats the cost saving the holding page exists to deliver. |
| Cloudflare Load Balancing | ~$12–15/mo | health probe (auto) | **Deferred.** Automatic failover is nice, but it adds always-on cost and a moving part not justified for a demo I park on a schedule I control. |
| Manual DNS flip via Cloudflare | ~$0 beyond the domain | manual `workflow_dispatch` | **Chosen.** I decide when the demo is up; a GitHub Action does the flip. No standing cost. |

### Mechanism

- `dinesafeviz.com` stays **proxied** (orange-cloud) through Cloudflare. The
  public DNS record always points at Cloudflare's anycast IPs and never
  changes, so there is no client-side DNS propagation to wait on. What changes
  is the **origin** Cloudflare proxies to, applied at the edge in seconds.
- Two states behind that one stable hostname:
  - **Parked (default):** a Cloudflare rule serves the static holding page.
    Until the holding page is built, this is a **302** redirect to the GitHub
    repo — 302 not 301, so the destination can change later without
    browser-cached redirects fighting the switch.
  - **Live:** the rule points the origin at the AKS ingress.
- A GitHub Actions `workflow_dispatch` job performs the flip with **one scoped
  Cloudflare API call** (a token that may edit DNS/origin rules on this one
  zone and nothing else, stored as a repo secret). The Cloudflare portal is
  setup-only, with no console login in the day-to-day.
- The **holding page is the fail-safe default.** A failed or half-finished
  deploy leaves `dinesafeviz.com` on the holding page, never on a 502.

### Ordering (avoid flapping and split state)

- **Wake:** `terraform apply` AKS → wait for ingress readiness/health → *then*
  flip the origin to the cluster.
- **Park:** flip the origin to the holding page *first* → *then*
  `terraform destroy` / scale to zero.

This order ensures the public hostname never points at a cluster that isn't
ready, and it never stays pointed at a cluster being torn down.

### Relationship to the regional DR cutover

Same pattern, different trigger and blast radius. The DR cutover described
later rebuilds a cluster in a second region after a real outage, while the
holding-page flip parks a healthy demo to save money. Both are manual
`workflow_dispatch` jobs that end in a DNS-layer swap and a smoke test, and
both keep the runbook in GitHub Actions so it never depends on the cluster
it is pointing away from.

### Framing: a cost hack that is also release engineering

> Parking the demo to save money is, mechanically, a blue-green cutover behind
> a stable load-balancer address. The public hostname never moves, and I swap
> what sits behind it between two "colours" — the live AKS cluster and a static
> holding page — and the holding page is the safe default I fail back to. The
> cutover is a *manual trigger over an automated, version-controlled process*:
> a `workflow_dispatch` button runs the exact API call from the repo, every
> flip lands in the Actions log, and the token is scoped and rotatable. So the
> same money-saving switch also demonstrates blue-green deployment, fail-safe
> defaults, GitOps cutover, and least-privilege automation. The constraint —
> don't pay for idle compute — produced the design, which is how good release
> engineering usually happens.

**Roadmap note.** The holding page itself (recorded GIFs of the running app,
deployment, DR, and monitoring, plus a walkthrough video) waits for a later
phase, because filming it requires a working AKS deployment to record. Until
then, `dinesafeviz.com` 302-redirects to the repo through a Cloudflare
redirect rule.

## Scheduled jobs and DR runbooks

Planning notes for the backup-and-DR phase (post-v0.4). Captures where each
scheduled job should run and why. Not implemented yet.

### Guiding principle

Choose the runtime for each scheduled job based on **where its dependencies
live** and **what must still be available when the job runs**:

- Jobs that talk to in-cluster services (the PostgreSQL pod, ETL state)
  belong in **Kubernetes** — close to their dependency, on the private
  cluster network, using the same secrets and identity story as the rest of
  the workload.
- Jobs that move Azure resources around without touching the cluster belong
  in **GitHub Actions** — auditable, version-controlled, OIDC-authenticated,
  observable in a UI that does not depend on AKS being healthy.
- The DR cutover workflow belongs in **GitHub Actions specifically** because
  the primary region may be down when it runs. The runbook should not depend
  on the thing it is recovering from.

### Per-job placement

| Job | Where | Why |
|---|---|---|
| 00:30 ETL data refresh (DineSafe pull → PostgreSQL) | Kubernetes CronJob | Writes to in-cluster PostgreSQL over the private cluster network. GitHub Actions would require exposing PG publicly or running a self-hosted runner inside the cluster — both worse than a CronJob. |
| 02:00 DB backup (base backup + WAL archive) | CloudNativePG `ScheduledBackup` CRD | The operator owns backup orchestration natively — continuous WAL archiving plus scheduled base backups to Azure Blob. A hand-rolled CronJob calling `az snapshot create` on the underlying managed disk would not produce a consistent PG snapshot without first quiescing the DB. |
| 02:15 Cross-region snapshot / blob replication | GitHub Actions scheduled workflow | Pure Azure-to-Azure data movement; does not touch the cluster. GHA is auditable, version-controlled, observable from outside the primary region. Authenticates to Azure via OIDC federation, no long-lived secrets. |
| DR cutover (failover to DR region) | GitHub Actions, `workflow_dispatch` (manual) | Multi-step orchestration: `terraform apply` DR cluster → bootstrap CloudNativePG from replicated WAL → deploy app → DNS swap → smoke test. Cannot live in the primary cluster (the thing that is down). Manual trigger with a required confirmation input gives a break-glass with an audit trail. |

### Cross-cutting best practices

- **One identity story per surface.** In-cluster jobs use Azure Workload
  Identity (federated Kubernetes service account → Entra managed identity →
  least-privilege Azure RBAC). GitHub Actions uses GitHub OIDC federation to
  a separate Entra app registration with its own least-privilege role. No
  long-lived PATs or client secrets in either place.
- **Idempotency.** Every scheduled job must be safe to re-run. The ETL
  detects "already loaded this day's snapshot." The replication job uses
  `azcopy sync`, which is idempotent by design. CronJobs set
  `concurrencyPolicy: Forbid` so a hung run cannot overlap with the next.
- **Time zones.** Pin every cron expression — Kubernetes CronJob
  `spec.timeZone` and GitHub Actions cron syntax — to a single explicit
  zone (`America/Toronto` or UTC, chosen once and used everywhere). Implicit
  UTC with mental conversion is how 02:00 jobs end up running at 21:00.
- **Failure surfacing.** Each job emits either a Prometheus job-completion
  metric (CronJob → exporter → on-prem Prometheus) or a GitHub status that
  routes to a notification channel. A silently failing backup is worse than
  no backup.
- **DR cutover guardrails.** The cutover workflow requires a manual
  `confirm` input, a current AKS health check against the primary (so it
  refuses to fire when the primary is actually up), and a dry-run mode for
  rehearsal. Schedule a quarterly cutover drill — it is the only way to
  know the runbook still works.
- **No DR dependency on the failed region.** State the cutover workflow
  needs — Terraform remote state, container images, secrets — must already
  live in a region-independent location: Terraform state in a geo-redundant
  storage account (or a second copy in the DR region), images mirrored to a
  DR-region ACR, secrets in a Key Vault reachable from outside the dead
  region.

### Why not run everything in GitHub Actions

Uniformity and audit trail make GHA-everywhere tempting. It falls down on:

- **Network reach.** Anything writing to in-cluster PostgreSQL would need
  either a public DB endpoint (security regression) or a self-hosted GHA
  runner inside the cluster (re-introduces the in-cluster compute it was
  trying to avoid).
- **Free-tier minute limits.** GitHub Actions includes 2,000 free
  minutes/month on private repos, and unlimited minutes on public repos.
  Three nightly jobs stay well within budget, so flag this if the job
  count grows.
- **Coupling DR to GitHub uptime.** Low-probability but real. This is
  acceptable for this project. In a regulated environment, the cutover
  runbook would also need to run manually from `az` CLI on a
  workstation as a fallback.