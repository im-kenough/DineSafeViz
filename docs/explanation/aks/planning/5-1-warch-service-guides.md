# 5-1. Select Azure services — service guides

Step 5 of the [Well-Architected Framework process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process) is to select the right Azure services and configure them correctly. A [service guide](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/) is *vertical*: it takes a single Azure service and reviews it through all five pillars, highlighting the features that matter most for a well-architected baseline.

## Summary

DineSafeViz uses a small slice of the ~30 services in the [catalog](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/?product=popular). Four apply directly — **AKS** (primary), **Blob Storage**, **Load Balancer**, and **Log Analytics** — and one applies only partially:

- **The self-hosted-database gap.** DineSafeViz runs PostgreSQL on the cluster with the [CloudNativePG](https://cloudnative-pg.io/) operator, not the managed [Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/postgresql). The managed service guide's reliability advice (HA replicas, zone-redundant PITR, automated backup) assumes Azure operates the database — so it only *partially* transfers. Those same reliability concerns are instead answered by the design guides in [5-2](5-2-warch-design-guides.md): [health modeling](5-2-warch-design-guides.md#health-modeling), [disaster recovery](5-2-warch-design-guides.md#disaster-recovery-plan), and [handling transient faults](5-2-warch-design-guides.md#handling-transient-faults).
- **The no-guide gap.** Some in-use services aren't in the catalog at all — most notably **Key Vault**, which DineSafeViz relies on through the CSI Secrets Store driver. For those, the pillar guidance lives only inside other service guides (the AKS guide names the Key Vault + CSI pattern under Security) rather than in a dedicated page.

## Service guides

### Azure Kubernetes Service — *Applicable (primary)*

> Source: [Architecture best practices for Azure Kubernetes Service (AKS)](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service)

AKS is the platform the entire workload runs on, so this guide carries the most weight. The guide splits every recommendation into *cluster* concerns (the admin's responsibility) and *workload* concerns (the developer's) — a split that maps neatly onto a solo operator wearing both hats.

- **What the guide covers:** choosing and configuring AKS across all five pillars — node-pool topology, availability zones, identity and network security, pricing tiers and autoscaling for cost, IaC and observability for operations, and scaling strategy for performance.
- **How it applies to DineSafeViz:**
  - **Reliability** — The guide's central reliability levers (availability zones, multi-region clusters, the uptime SLA, Azure Backup for AKS) are all *deliberately declined* per the cost-first tradeoffs in [Step 3](3-warch-tradeoffs.md): single region, no zones, AKS **Free** tier (no SLA), clusters stopped by default. The recommendations that **are** adopted are the free, workload-side ones: liveness/readiness probes, pod resource requests and limits, and isolating system pods from application pods.
  - **Security** — Strong alignment. The guide's top recommendations are already in place: **Workload Identity (OIDC)** for credential-free access to Azure resources, **managed identities** on the cluster, and the open-source **Workload ID + Secrets Store CSI driver with Key Vault** pattern it names explicitly. Network segmentation is met with **Cilium** NetworkPolicy (default-deny) rather than the Azure/Calico option the guide lists. The premium items — private cluster, Azure Firewall egress control, **Defender for Containers**, a WAF — are declined or deferred as risk-accepted extras, consistent with Step 3's "never trade away core controls, only premium monitoring."
  - **Cost Optimization** — The guide reads like the DineSafeViz cost model: **AKS Free** tier, **Spot** VMs (up to ~90% off) on **B2s burstable** SKUs, cluster autoscaler and scale-to-zero, small images for fast node startup, right-sized SKUs. Azure Reservations are declined (they assume steady-state; the cluster is off by default and eviction-tolerant).
  - **Operational Excellence** — Adopted at the workload's OE Level 1 maturity: **IaC** (Terraform), templated releases (Helm/Helmfile), CI via **GitHub Actions**, and a monitoring strategy through Log Analytics / Container Insights. Advanced items (GitOps controllers, Azure Chaos Studio, blue-green stamps) are out of scope for a single small workload.
  - **Performance Efficiency** — Lightweight by design. Capacity planning is trivial (~10 concurrent connections, a <1s query budget), so cluster autoscaler + a single user node pool cover it. HPA/KEDA and per-flow node-pool isolation are noted but unnecessary at this scale.

### Azure Blob Storage — *Applicable*

> Source: [Architecture best practices for Azure Blob Storage](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-blob-storage)

- **What the guide covers:** durability and redundancy tiers (LRS/ZRS/GRS), access tiers for cost, encryption and network access for security, and lifecycle management.
- **How it applies to DineSafeViz:** Blob Storage is the **backup target** — CloudNativePG streams WAL archives and basebackups here. The guide's **redundancy** choice is the key decision: **GRS** (geo-redundant) is used so the backup survives a regional loss even though the cluster itself is single-region — the one place the design pays for cross-region durability, because it underpins the ≤24h RPO. Access is scoped through Workload Identity (no account keys), matching the guide's security guidance.

### Azure Load Balancer — *Applicable*

> Source: [Architecture best practices for Azure Load Balancer](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-load-balancer)

- **What the guide covers:** SKU choice (Basic vs Standard), health probes, zone redundancy, and outbound-connection (SNAT) planning.
- **How it applies to DineSafeViz:** The load balancer isn't provisioned directly — it's created by the **nginx ingress** Service of type `LoadBalancer`. So the guide applies indirectly: it explains the resource AKS stands up on the workload's behalf. Zone redundancy is moot (single zone), and SNAT-exhaustion concerns don't arise at ~10 concurrent connections, so the guide mostly confirms that the defaults are adequate here.

### Log Analytics — *Applicable*

> Source: [Architecture best practices for Log Analytics](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-log-analytics)

- **What the guide covers:** workspace design, data collection and retention, access control, and cost control on ingestion/retention.
- **How it applies to DineSafeViz:** Log Analytics is the observability backend for cluster and workload telemetry. The guide's **cost/retention** guidance is the operative one: a **30-day** retention window keeps ingestion and storage inside the $100/mo cap while still supporting incident investigation — and it happens to match the health-modeling guide's "don't retain health data beyond 30 days" recommendation ([5-2](5-2-warch-design-guides.md#health-modeling)).

### Azure Database for PostgreSQL — *Partial (self-hosted instead)*

> Source: [Architecture best practices for Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/postgresql)

- **What the guide covers:** the *managed* PostgreSQL service — built-in HA, read replicas, zone-redundant deployment, automated backup with PITR, and connection pooling, all operated by Azure.
- **How it applies to DineSafeViz:** Only partially, because the database is **self-hosted with CloudNativePG**, not the managed service. The *pillar goals* still apply — durable backups, point-in-time recovery, connection limits — but the *mechanisms* are owned by the operator, not Azure: 7-day PITR and basebackup/WAL to Blob GRS are configured in CloudNativePG rather than clicked on in a managed service. This is the clearest example of the vertical service-guide grid not covering a self-hosted component; the horizontal design guides in [5-2](5-2-warch-design-guides.md) pick up the slack.

## Not covered by a service guide

- **Azure Key Vault** — no dedicated WAF service guide exists, despite being in active use via the CSI Secrets Store driver. Its pillar guidance is embedded in the AKS guide's Security section instead.
- **Azure Firewall, Application Gateway, Front Door, Traffic Manager** — in the catalog but **not used**. They're declined on cost grounds (Step 3): Cilium NetworkPolicy plus the nginx ingress cover segmentation and routing at this scale, so the managed network appliances aren't justified.
