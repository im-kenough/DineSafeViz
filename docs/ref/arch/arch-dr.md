# Disaster Recovery & Resiliency

## Scenario

### City of Toronto Open Data Portal is unavailable

TO do: https://github.com/im-kenough/DineSafeViz/issues/62


### AKS Backup and Recovery

To do: https://learn.microsoft.com/en-us/azure/architecture/operator-guides/aks/aks-backup-and-recovery

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
  minutes/month on private repos; unlimited on public repos. Three nightly
  jobs is well within budget; flag this if the job count grows.
- **Coupling DR to GitHub uptime.** Low-probability but real. Acceptable
  for this project; in a regulated environment the cutover runbook would
  also be runnable manually from `az` CLI on a workstation as a fallback.