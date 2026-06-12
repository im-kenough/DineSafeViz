# Architecture - Design decisions

This document explains how the DineSafeViz Azure Kubernetes Service
(AKS) deployment maps to Microsoft's published reference architectures
and to the Azure Well-Architected Framework (WAF). It captures scope,
intentional divergences from the reference, and items deliberately
deferred to later phases.

The deployment implements a cost-optimized adaptation of the
**AKS Baseline Architecture** augmented with a **passive-cold
disaster recovery** pattern (cross-region replicated Postgres WAL
archive, no running secondary cluster). Phase 2 evolves toward the
**AKS Baseline for multi-region clusters** as a configuration change
rather than a redesign.

The full implementation spec is in
[`docs/superpowers/specs/2026-06-09-aks-deployment-design.md`](../../superpowers/specs/2026-06-09-aks-deployment-design.md);
this doc is the design-rationale companion to that spec. The reading
list driving each section below is in
[`arch-checklist.md`](arch-checklist.md).

> [!NOTE]
> Sections marked **TODO** require completing the corresponding item in
> [`arch-checklist.md`](arch-checklist.md) and capturing concrete
> scope-in / scope-out items from the Microsoft checklist.

## Context

DineSafeViz is a personal portfolio project that visualizes Toronto
Public Health DineSafe food safety data. Its primary purpose is to
demonstrate operational excellence — modern enterprise patterns,
well-structured documentation, security and privacy as first-class
concerns — at a personal-budget cost level.

The hosting target is two AKS clusters (production and staging) in
East US 2, **stopped by default** and brought up on demand for demos
and development. Steady-state cost target: $25 to $50 per month.

## Scope

### In scope

- A reference-anchored AKS deployment that a reviewer can recognize as
  modern enterprise practice.
- A small set of WAF pillars adapted to the personal-budget context,
  with explicit rationale for each divergence.
- A disaster recovery pattern pre-positioned for Phase 2 activation
  without re-architecting the data layer.
- Documentation sufficient for a new operator to bring the system up,
  deploy a change, and recover from common failure modes.

### Out of scope (Phase 1)

- A 24/7 availability SLA. The site is reachable only when a cluster
  is manually started.
- Multi-region active-active. The secondary region is cold.
- Mission-critical workload guarantees (recovery time objectives
  measured in minutes, financial loss avoidance, regulated compliance).
- Enterprise-scale governance: central policy, multi-subscription
  management groups, hub-spoke shared services.
- Paid security add-ons that are not free-tier (Microsoft Defender for
  Containers, Application Gateway WAF, Azure Firewall).

## Reference architectures implemented

### Modified AKS Baseline Architecture

The Phase 1 deployment is a **cost-optimized adaptation** of the
[AKS Baseline Architecture][aks-baseline]. The full conformance table is
in the next section; key divergences are:

- **No hub-spoke network topology.** A single VNet per environment.
  DineSafeViz is single-subscription with no shared services to
  centralize.
- **Public AKS API server** (IP-allowlisted to workstation and GitHub
  Actions runner ranges) instead of a private endpoint. Removes the
  need for Azure Bastion.
- **NGINX Ingress + Standard Load Balancer + static Public IP**
  instead of Application Gateway with WAF. Saves approximately $26
  per month per environment.
- **Default AKS-managed outbound load balancer** instead of Azure
  Firewall egress. Saves approximately $30 per month per cluster.
- **ACR Basic and Key Vault with public endpoints** instead of Private
  Endpoint variants. Private Endpoint requires Premium ACR and Premium
  Key Vault tiers; the cost is not defensible at this scale.
- **CloudNativePG in-cluster** instead of Azure Database for
  PostgreSQL. Free CNCF operator with CNCF-grade backup / point-in-time
  recovery via Barman cloud.

Each divergence is rationalized below in the
[Conformance table](#aks-baseline-conformance-table).

### Passive-cold disaster recovery

The deployment matches the [passive-cold solution for AKS]
[passive-cold] pattern: production runs in East US 2; the disaster
recovery site is pre-positioned in West US 2 but is **not running** in
Phase 1.

Data replication is implemented now so the DR cluster can be activated
as a Phase 2 configuration change:

- CloudNativePG writes WAL segments and daily basebackups to an Azure
  Blob storage account with **geo-redundant storage (GRS)**.
- The secondary region's read-only endpoint (`-secondary`) is the
  source the DR cluster will use when promoted.
- Recovery point objective: at most 24 hours.
- Recovery time objective: at most 4 hours (manual cluster start and
  promotion).

The Phase 2 DR activation runbook (RB-16) is named in the spec but not
yet authored.

### Phase 2: AKS Baseline for multi-region clusters

The Phase 2 enhancement target is the
[AKS Baseline for multi-region clusters][aks-multi-region]. Phase 1
decisions made with Phase 2 in mind:

- WAL archive in GRS storage. Promotion does not require a data
  migration.
- Identical Terraform module structure for `azure-prod` and the future
  `azure-prod-wus2`. The DR cluster is a parallel instantiation, not a
  separate codebase.
- DNS managed by Azure DNS. A failover updates an A record; no
  registrar change required.
- Container images in ACR are region-replicated when ACR Basic is
  promoted to Premium in Phase 2 (small cost increase, planned).

Explicitly deferred to Phase 2:

- An always-on secondary cluster.
- Azure Front Door or Traffic Manager for automated regional failover.
- Active-active or hot-warm replication topologies.

## AKS Baseline conformance table

The following table maps each component of the AKS Baseline reference
to the DineSafeViz Phase 1 implementation. Status is one of: **Matches**
(implemented as in the reference), **Modified** (implemented
differently with rationale), **Out of scope** (not implemented; named
here so a reviewer knows it was considered).

| Baseline component | DineSafeViz Phase 1 | Status | Rationale |
|---|---|---|---|
| Hub-spoke VNet topology | Single VNet per environment | Modified | Single subscription; no shared services to centralize. |
| Multi-zone node pools | Multi-AZ pool definitions, min = 1 per pool | Modified | Pool spec is zone-capable; steady-state min held at 1 for idle cost. Multi-AZ activates on autoscale. |
| Private AKS API server | Public API, IP-allowlisted | Modified | Avoids Azure Bastion cost (~$140/mo). Phase 2 enhancement. |
| Azure Bastion for admin access | Not deployed | Out of scope | Follows from public API choice. |
| Azure Firewall egress filtering | Default AKS outbound load balancer | Out of scope | ~$30/mo per cluster; not defensible at this scale. |
| Application Gateway with WAF | NGINX Ingress + Standard LB + static PIP | Modified | $4/mo PIP vs ~$30/mo AGW. WAF deferred to Phase 2. |
| Microsoft Entra Workload Identity | Per-pod-class user-assigned managed identities | Matches | Required for the OIDC pattern. |
| ACR with Private Endpoint | ACR Basic, public endpoint, AcrPull via managed identity | Modified | Private Endpoint requires Premium ACR. Cost-prohibitive in Phase 1. |
| Key Vault with Private Endpoint | Key Vault RBAC mode + CSI Secrets Store, public endpoint | Modified | Same cost rationale as ACR. |
| Microsoft Defender for Containers | Not enabled | Out of scope | ~$7/vCPU/mo. Cost-prohibitive. |
| Azure Policy for AKS | Not enabled | Out of scope | Complexity vs benefit at single-tenant scale. |
| Container Insights + Azure Monitor | Container Insights, 30-day retention in `log-dsv-shared-eus2` | Matches | Free with Log Analytics workspace. |
| Network policy (Calico or Cilium) | Cilium, default-deny per namespace | Matches | Modern AKS option; demonstrates network security baseline. |
| Azure CNI Overlay | Azure CNI Overlay | Matches | Modern AKS default. |
| Cluster autoscaler | Enabled (`syspool` 1-2, `usrpool` 1-3) | Matches | Standard pattern. |
| User-assigned managed identity for cluster | Per-environment control-plane identity | Matches | Required for OIDC and Workload Identity. |
| Image vulnerability scanning | Not enabled | Out of scope | Phase 2 enhancement (Trivy or ACR Defender). |
| Pod Security Standards | Default profile | Modified | Restricted profile deferred to Phase 2. |
| Managed database service | CloudNativePG in-cluster (Postgres 17) | Modified | Free CNCF operator with PITR. Azure DB for PostgreSQL flexible-server entry SKU adds ~$15/mo per env. |

## Well-Architected Framework pillar assessment

Each subsection captures what is scope-in, scope-out, or modified for
that pillar. The TODO blocks call out checklist items that need
verification against Microsoft's per-pillar guide; complete each as the
corresponding row in [`arch-checklist.md`](arch-checklist.md) is read.

### Reliability

**Scope-in:**

- Multi-AZ-capable node pools (zones `[1, 2, 3]` on both pools).
- CloudNativePG operator with automatic pod restart and PVC re-mount.
- Daily basebackup plus continuous WAL archive to GRS storage. Recovery
  point objective ≤ 24h; recovery time objective ≤ 4h.
- Static Public IP per cluster (survives ingress controller restart;
  DNS record stays valid).
- Monthly cert renewal heartbeat workflow forces cluster start during
  long idle periods, preventing certificate expiry.
- Weekly backup verification workflow (`db-backup-verify.yml`) opens a
  GitHub issue if the latest basebackup is older than 48 hours.

**Scope-out (Phase 1):**

- AKS Free control plane has no uptime SLA. Acceptable because the
  cluster is stopped by default.
- Single-instance Postgres (`spec.instances: 1`). Multi-replica HA is a
  Phase 2 enhancement.
- No Horizontal Pod Autoscaler. The system is not under real user
  traffic in Phase 1.
- No active secondary region. Passive-cold only.

**TODO** (after reading the WAF Reliability checklist):

- Map each Microsoft reliability recommendation to a scope-in,
  scope-out, or modified item here.
- Verify whether any "must-have" reliability item is currently scope-
  out without rationale.

### Security

**Scope-in:**

- Microsoft Entra Workload Identity for every pod-to-Azure authentication
  path. No `imagePullSecret`. No client secrets in pods.
- GitHub Actions OIDC federation. No long-lived secrets in GitHub
  Actions. Per-environment identity scoping with separate federated
  credentials for `prod`, `staging`, and `shared`.
- Azure Key Vault per environment in RBAC mode. Soft-delete (90 days)
  and purge protection enabled.
- Cilium NetworkPolicy with default-deny per namespace. Explicit allow
  rules for app-to-Postgres, app-to-DNS, app-to-ACME, app-to-Azure-Blob.
- Per-environment isolation: separate AKS clusters, Key Vaults, managed
  identities, WAL storage accounts, and Public IPs.
- GitHub Environments approval gate on production deploys
  (`im-kenough` is the required reviewer).
- Workstation and GHA runner IP allowlist on the AKS API server.

**Scope-out (Phase 1):**

- Microsoft Defender for Containers (cost).
- Azure Policy for AKS (complexity).
- Private AKS API server endpoint and Azure Bastion (Phase 2).
- Azure Firewall egress filtering (cost).
- Pod Security Standards Restricted profile (Phase 2).
- Image vulnerability scanning (Phase 2).
- Application Gateway WAF (Phase 2).

**TODO** (after reading the WAF Security checklist):

- Confirm coverage of the Microsoft "secure access to the cluster
  resources" recommendations.
- Capture any "must-have" security item not addressed by the spec.

### Cost optimization

This is the strongest pillar; most of the design is driven by it.

**Scope-in:**

- Stop-by-default cluster lifecycle via `aks-down.yml` (and the
  inverse `aks-up.yml`). Reduces steady-state cost to control-plane
  zero plus storage and managed identities.
- AKS Free control plane tier. Saves ~$73/mo per cluster vs Standard.
- B2s burstable VMs for both system and user pools.
- Spot user pool capped at on-demand price.
- Standard SSD (E10) storage class; not Premium SSD.
- Azure Monitor budget alert at 80% of $50/mo cap.
- Azure Monitor alert when an AKS cluster runs continuously for more
  than 12 hours (cost guardrail against a forgotten cluster).
- LRS storage for staging WAL (DR not needed for non-production data).

**TODO** (after reading the WAF Cost Optimization checklist):

- Confirm coverage of the "right-size" and "scale to zero" Microsoft
  recommendations.
- Verify whether resource tagging is sufficient for the Microsoft cost
  reporting recommendations. Current tags: `workload`, `environment`,
  `managed_by`, `cost_center`, `owner`, `repo`.

### Operational excellence

**Scope-in:**

- Infrastructure as Code: Terraform per environment, Helm for in-
  cluster resources, Helmfile for orchestration. No portal clicks.
- Remote Terraform state in Azure Blob with native blob-lease locking.
- GitHub Actions workflows for every operation (cluster lifecycle, app
  deploy, infra change, secret rotation).
- Per-environment identity scoping. The `prod` identity cannot touch
  `staging` resources.
- GitHub Environments approval gate for production.
- Comprehensive runbook catalog (RB-01 through RB-16).
- Centralized logging via Container Insights into a single shared Log
  Analytics workspace, 30-day retention.
- Scheduled verification workflows: cert renewal heartbeat, backup
  verification, ACR untagged-image cleanup.
- This documentation set, anchored by the spec, the conformance table
  above, and the runbook index.

**Scope-out (Phase 1):**

- GitOps controller (Argo CD or Flux). Deferred to Phase 3.
- Per-PR preview environments. Deferred to Phase 2.
- Distributed tracing. Deferred to Phase 2.
- Synthetic end-to-end tests. Deferred to Phase 2.

**TODO** (after reading the WAF Operational Excellence checklist):

- Confirm coverage of the deployment, monitoring, and incident-
  response recommendations.
- Cross-check the runbook catalog (RB-01..RB-16) against the
  Microsoft Day-2 operations guide. Likely gap: an AKS version
  upgrade runbook.

### Performance efficiency

**Scope-in:**

- Resource requests on the Postgres `Cluster` CR (`250m` CPU,
  `512Mi` memory in prod).
- Standard SSD (E10) sized to the workload's IOPS budget. The dataset
  is small (Toronto Open Data DineSafe CSV).
- Spot user pool for stateless workloads where eviction is acceptable.

**Scope-out (Phase 1):**

- Horizontal Pod Autoscaler. Deferred to Phase 2 (requires a load
  test).
- Load testing (k6). Deferred to Phase 2.
- PgBouncer connection pooling. Deferred to Phase 2.
- Postgres read replicas for analytics offload. Deferred to Phase 3.

**TODO** (after reading the WAF Performance Efficiency checklist):

- Confirm whether the Microsoft recommendations for cluster sizing,
  storage tier selection, and workload scaling are addressed.

## Reference architectures explicitly out of scope

These are named so a reviewer knows they were considered and
consciously excluded.

- **[AKS Landing Zone Accelerator][aks-lza].** Targets enterprise-scale
  multi-subscription estates with central policy and hub-spoke shared
  services. DineSafeViz is single-subscription and single-tenant.
- **[Mission-critical workload guidance][mission-critical].**
  DineSafeViz is a portfolio demo. There is no business continuity
  requirement, regulatory compliance scope, or financial loss
  avoidance to justify mission-critical patterns.

## Decision log

Ad-hoc decisions taken during implementation are captured here in
date order. Each entry: date, decision, rationale, affected design
sections.

_Empty. To be populated as implementation proceeds._

## References

- AKS Baseline Architecture:
  https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks/baseline-aks
- Passive-cold solution for AKS:
  https://learn.microsoft.com/en-us/azure/aks/passive-cold-solution
- AKS Baseline for multi-region clusters:
  https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-multi-region/aks-multi-cluster
- AKS Well-Architected service guide:
  https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service
- AKS Day-2 operations guide:
  https://learn.microsoft.com/en-us/azure/architecture/operator-guides/aks/day-2-operations-guide
- AKS Landing Zone Accelerator:
  https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/scenarios/app-platform/aks/landing-zone-accelerator
- Mission-critical workloads (Well-Architected):
  https://learn.microsoft.com/en-us/azure/well-architected/mission-critical/mission-critical-overview
- Implementation spec:
  [`docs/superpowers/specs/2026-06-09-aks-deployment-design.md`](../../superpowers/specs/2026-06-09-aks-deployment-design.md)
- Reading checklist: [`arch-checklist.md`](arch-checklist.md)

[aks-baseline]: https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks/baseline-aks
[passive-cold]: https://learn.microsoft.com/en-us/azure/aks/passive-cold-solution
[aks-multi-region]: https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-multi-region/aks-multi-cluster
[aks-lza]: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/scenarios/app-platform/aks/landing-zone-accelerator
[mission-critical]: https://learn.microsoft.com/en-us/azure/well-architected/mission-critical/mission-critical-overview
