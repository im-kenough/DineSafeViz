# Architecture Design planning

## Architecture Style
The DineVizSafe application considers Design solutions from the Azure Architecture Centre. It

The context of this repo is to demonstrate good DevOps and Cloud Systems Engineering practices, so I'll be deploying this in AKS.

The app is a N-tier architecture, single-region, with role-segmented data-tier access and a shared-database read pattern between the application and the analytics dashboard.

### Best practices

- Use autoscaling to handle changes in load. For more information, see Autoscaling best practices.
  - Will use AKS

- Use asynchronous messaging to decouple tiers.
- Cache data that doesn't change often. For more information, see Caching best practices.

- Configure the database tier for high availability by using a solution such as SQL Server Always On availability groups.

- Place a WAF between the front end and the internet.

- Place each tier in its own subnet, and use subnets as a security boundary.
- Restrict access to the data tier by allowing requests from a middle tier only.
  - Don't want to pay for a load balancer

## [Design Principles](https://learn.microsoft.com/en-us/azure/architecture/guide/design-principles/) for Azure Applications

### Core Principles
- Design for self-healing
  - health checks are built into the app and will plug into a future monitoring solution
  - Utilizing AKS will provide self healing in some areas
- Make all things redundant
  - Utilizing AKS will provide self healing in some areas
  - DB read replicas will provide resiliency
  - DR region is in roadmap
- Minimize coordination
  - Dependencies are minimized where practical.
  - Will use Terraform with state saved to Azure Blob to maintain infrastructure consistency
- Design to scale out
  - AKS and VMSS are used to horizontally scale out. This is a demo application, so serious traffic is not expected.
- Partition around limits
  - DineSafeViz has a small footprint and will not approach Azure feature limits.

### Operational Principles
- Design for operations
  - IAC will be implemented to consistently deploy app
  - Monitoring, Centralized logging, Observability is on the road map, which will facilitate incicent response
- Use managed services
  - Will consider PaaS depending if a free / low cost tier is available
- Use an identity service
  - will use Managed Identities to ...

### Strategic principles
- Design for evolution
  - an automated CI/CD pipeline with robust IAC will allow the app to accomodate future growth and design changes
- Build for the needs of business
  - Business Objectives:
  - To be determined
    - Recovery Time Objectives (RTOs)
    - Service Level Agreements (SLAs)
    - Service Level Objectives (SLOs)
    - Maximum Tolerable Outage (MTO)
- Perform failure mode analysis for services
  - to do: conduct failure mode analysis (FMA) during architecture and design phases. Rate each failure mode by risk and impact, then determine appropriate response and recovery mechanisms.



## [Technology choices](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/technology-choices-overview) for Azure solutions


### Tecnology Choicses Summary

- Compute Service: AKS
- Container Option: AKS
- Hybrid Service: None, but maybe Azure Arc in the future.
- Identity Service: MS Entra ID
- Storage Service:
  - OS disk: Standard HDD, upgrade to Standard SSD in Q1 2028
  - Data disk (PostgreSQL PVC): Standard HDD
  - Object storage: Azure Blob Storage (Terraform remote state)
  - Data transfer: Azure CLI, AzCopy, or Azure PowerShell
  - Redundancy: Local Redundant Storage
- Data Store: Self-hosted PostgreSQL on AKS, managed by the CloudNativePG operator

### Choose a compute service

Q: What compute service do I choose?

A: AKS

This app will use Azure Kubernetes Service.

[Considerations](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree)

![Choose AKS](/docs/img/tech-choose-aks.png)

#### Decision tree path

DineSafeViz is a greenfield (build-new) workload, not a migration. Following the
decision tree:

1. Need full IaaS control? **No** — want managed infrastructure where practical
2. HPC or batch processing? **No**
3. Event-driven / serverless triggers? **No** — serves HTTP pages continuously
4. Managed web hosting only (no containers)? **No** — container orchestration is
   the point
5. Need container orchestration? **Yes**
6. Need direct Kubernetes API and control plane access? **Yes** → **AKS**
   (Container Apps abstracts away the K8s API, reducing demonstration value)

#### Candidates evaluated

| Service | Decision | Reason |
|---|---|---|
| Azure Virtual Machines | Rejected | IaaS; full OS/patching overhead; could host the app but teaches nothing new about container ops |
| Azure App Service | Rejected | PaaS web hosting only; no Kubernetes exposure; suited to web-queue-worker style, not N-tier with container ops |
| Azure Functions | Rejected | FaaS / event-driven compute; no fit for a continuous page-serving web app |
| Azure Kubernetes Service | **Selected** | Managed Kubernetes; exposes control plane and K8s API directly; widely used enterprise tool for DevOps showcase |
| Azure Container Apps | Rejected | Built on Kubernetes but hides the K8s API; reduces hands-on orchestration demonstration value |
| Azure Container Instances | Rejected | Runs a single container group with no orchestration layer; too simple for a DevOps showcase |
| Azure Red Hat OpenShift | Rejected | Not applicable — no OpenShift requirement or existing investment |
| Azure Batch | Rejected | Not applicable — HPC/parallel processing workload |
| Azure VMware Solution | Rejected | Not applicable — VMware workload migration only |

#### Traditional [Web App vs Single Page App](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/choose-between-traditional-web-and-single-page-apps)

DineSafeViz is a traditional web app. The Microsoft decision criteria confirm this:

- **Read-only client-side requirements** — every page is read-only; no user
  creates, edits, or submits data
- **Public-facing with SEO benefit** — no auth wall; static, bookmarkable URLs
  per page benefit from search engine indexing
- **No rich interactive UI** — the inspections page is a table, home is stats,
  and the dashboard is an embedded iframe; no drag-and-drop or complex form flows
- **No existing API to expose** — there is no web API contract driving a need
  for a SPA front-end

A SPA would be overkill for this use case. Blazor is not relevant because this
is not a .NET project.

### Choose a container option

The compute decision in the previous section already resolved the container
service question: AKS is the chosen platform. This section records why the other
container-specific options were set aside.

#### Candidates evaluated
Rejected

**Azure Container Apps** is the closest alternative. Per the
[compute options for microservices](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/compute-options)
comparison, Container Apps is a managed service built on top of Kubernetes with
Dapr integration, per-app scaling, and scale-to-zero — but it does not expose
the Kubernetes API or control plane. For a DevOps portfolio project the
hands-on K8s surface is the point, so Container Apps is ruled out.

**Azure Container Instances** can run the application image directly and is the
simplest path to a running container in Azure. It has no orchestration, no
scheduling, and no built-in health management. It is useful for one-off or
sidecar workloads but not suitable here.

**Kubernetes at the edge** (Arc-enabled K8s, etc.) is not applicable — this is
a single-region cloud deployment.



### Choose a hybrid service

This design design decision asks, "If you alaready have infrastructure that isn't in Azure how do you connect to it or run azure services on it?"

The application will be AKS hosted with monitoring infrastructure selfhosted in on prem VMs. While "Azure Arc enabled servers" pattern is the closest fit, it is not needed in my situation.



It's out of scope for now and will be revisited when the observability stack is deployed.

#### Decision tree path for the self-hosted observability VMs

![Choose AKS](/docs/img/tech-choose-hybrid.png)


#### Azure Hybrid Services
- **Azure Stack:** Offers various software and hardware solutions to bring Azure on prem to a client's data centre. Not needed for my situation.
- **Azure Arc**: Azure Arc-enabled servers installs a lightweight agent on each VM and makes it available in Azure Resource Manager. It enables self hosted VMs to access Azure services and be visible in Azure reports and configuration in a single pane of glass.
- **Azure IoT Edge:** is a device side runtime installed on Linux or Windows hosts that connects to Azure IoT Hub, so you can deploy cloud workloads on IoT devices. Designed to run on gateways or devices close to sensors and actuators. Not applicable to my situation.
- **Azure VMWare Solutions:** Offers bare metal VMWare vSphere clusters built on dedicated Azure hardware. Allows Azure integration while using VMware tools. Not applicable to my situation, not using VMWare.

#### Candidates evaluated
| Service | Decision | Reason |
|---|---|---|
| Azure Arc (Arc-enabled servers) | **Future candidate** | The self-hosted observability VMs are VM-based workloads on existing hardware — the exact scenario Arc-enabled servers is designed for. Deferred to the monitoring phase; not in scope for initial AKS deployment. |
| Azure Stack Hub | Rejected | Runs a full Azure control plane on-premises for disconnected or regulated environments. Reviewed the [Azure Stack Hub considerations](https://learn.microsoft.com/en-us/azure-stack/user/azure-stack-considerations) — it requires operator-managed hardware, custom API endpoints, and delivers only a subset of Azure services. No data sovereignty or air-gap requirement exists here; the overhead is unjustified. |
| Azure Local (HCI) | Rejected | Microsoft's Hyperconverged infrastructure solution for running VMs and containers on validated on-premises hardware clusters. The [Azure Local vs Windows Server](https://learn.microsoft.com/en-us/azure/azure-local/concepts/compare-windows-server) comparison shows it requires a minimum multi-node cluster, always-on Azure connectivity, and HCI-specific hardware. The self-hosted monitoring VMs are standalone machines, not an HCI cluster. Useful for regulatory or data sovernignty requirements. Not applicable to my situation; don't want to bring Azure on prem. |
| Azure Stack Edge | Rejected | A physical hardware appliance for edge data transfer and ML inference at remote or ruggedized locations. No edge location or near-real-time data processing requirement exists. |
| Azure IoT Edge / IoT Hub | Not applicable | Designed for mass IoT device management and on-device inference. Not an IoT application. |
| Azure VMware Solution | Not applicable | Runs VMware vSphere workloads natively on Azure bare metal. No VMware environment to migrate or extend. |

### Choose an identity service

This section evaluates a Microsoft Identity solution service for DineSafeViz. The app has no user authentication requirement and no on-premises Active Directory. The only identity concern is workload identity; AKS pods authenticating to Azure services (ACR, Key Vault) without storing credentials.

We will use **Microsoft Entra ID** , which comes standard with every Azure subscription, with no additional cost.

#### Candidates evaluated

Microsoft offers three [Identity and Access Management services](https://learn.microsoft.com/en-us/entra/identity/domain-services/compare-identity-solutions), a cloud native and on premesis option.

| Service | Decision | Reason |
|---|---|---|
| Microsoft Entra ID (with AKS Workload Identity) | **Selected** | Cloud-based identity and mobile device management that provides user account and authentication services for resources such as Microsoft 365, the Microsoft Entra admin center, or SaaS applications. AKS Workload Identity uses OIDC federation to bind a Kubernetes service account to an Entra managed identity, letting pods authenticate to Azure services without any stored credentials. |
| Microsoft Entra Domain Services | Rejected | A Microsoft Managed Azure hosted Domain controller. Rejected. Not applicable in my situation. Will be even more expensive than running my own domain controller. |
| Active Directory Domain Services (self-managed on VMs) | Rejected | Microsoft's on premesis self hosted LDAP server that provies IAM, object management, group policy and trust. Rejected, I'm not running a Windows Domain Controller. |

### Choose a storage service

DineSafeViz has three distinct storage needs:
- OS disks for AKS node pool VMs,
- a persistent volume for the PostgreSQL container
- object storage for Terraform remote state. 

The [Review your storage options](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/storage-options) article maps these needs to Azure Managed Disks for block storage and Azure Blob
Storage for object storage. No cloud-native file shares, HPC storage, big data
lake, or large-scale physical data transfer are required.

#### Select storage tools and services to support your workloads

Key questions:

1. Do your workloads require disk storage to support the deployment of infrastructure as a service (IaaS) virtual machines?
   - Yes. AKS node pool VMs require OS disks and PostgreSQL requires a persistent volume backed by block storage.
2. Do you need to consolidate that block storage across or are you migrating an on-premises SAN?
   - No.
3. Will you need to provide downloadable images, documents, or other media as part of your workloads?
   - No. Flask serves rendered HTML; no static media is served from blob storage.
4. Will you need a location to store virtual machine logs, application logs, and analytics data?
   - No. Will host on prem metrics, centralized logging and observability VMs.
5. Will you need to provide a location for backup, disaster recovery, or archiving workload-related data?
   - Yes. Blob Storage will store Terraform remote state. PostgreSQL backups are a future consideration for the DR roadmap.
6. Will you need to support big data analytics workloads?
   - No.
7. Will you need to provide cloud-native file shares?
   - No. PostgreSQL uses a block (ReadWriteOnce) persistent volume, not a shared file system.
8. Will you need to support high-performance computing (HPC) workloads?
   - No.
9. Will you need to perform large-scale archiving and syncing of your on-premises data?
   - No.
10. Do you want to expand an existing on-premises file share to use cloud storage?
    - No.

#### Azure Managed Disk types

The [disk types article](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types)
defines five tiers: Ultra Disk, Premium SSD v2, Premium SSD, Standard SSD, and
Standard HDD.

- **OS disk:** [Standard SSD](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types#standard-ssds) —
  recommended for web servers and lightly-used enterprise applications; lower
  cost than Premium SSD with consistent single-digit-millisecond latency.
- **PostgreSQL data disk (PVC):** [Standard HDD](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types#standard-hdds) —
  sufficient for a small, non-critical demo workload with low I/O frequency.
  Planned upgrade to Standard SSD in Q1 2028 if latency becomes a concern.

Note: Standard HDD OS disks are [retiring](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-hdd-os-retirement) on September 8, 2028. Can still be used as data storage sisks.

![Managed disk decision tree](/docs/img/tech-choose-managed-disk.png)

##### Data redundancy and availability

Azure Storage has various [redundancy and high availability options](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy): Locally redundant storage, Zone-redundant storage, Geo-redundant storage (GRS), Read-access GRS (RA-GRS), Read-access GZRS (RA-GZRS).

Locally Redundant Storage (LRS) is sufficient for my needs.

LRS replicates data to three disks within a data centre in the primary region. Can't specify an availability zone.

In an enterprise production app, at a minimum Zone Redundant Storage would be selected so one copy is replicated to each availability zone

#### Azure Blob Storage

Azure Blob Storage stores Terraform remote state, as noted in the design
principles section. The standard LRS hot tier is sufficient; no replication or
archival tier is needed for a state file workload.

#### Security

Azure Storage provides [several security controls](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/storage-options#security) relevant to this deployment.

**Encryption at rest** is enabled by default for all Azure managed disks, snapshots, and images using Microsoft-managed platform keys. No configuration is required. Azure Blob Storage is also encrypted at rest by default.

**Encryption at host** should be enabled on the AKS node pool. It extends encryption end-to-end from the VM through to the storage layer, covering temp disks, disk caches, and compute-to-storage data flows. Server-side encryption alone only covers data at rest on the storage clusters; encryption at host closes the remaining gap.

**Azure Disk Encryption (ADE)**, which uses BitLocker on Windows and dm-crypt on Linux, is [retiring on September 15, 2028](https://learn.microsoft.com/en-us/azure/virtual-machines/disk-encryption-overview). New VMs should use encryption at host instead. ADE will not be used in this deployment.

**Blob Storage access** for Terraform state is secured via Azure RBAC and Entra ID. HTTPS is enforced by default. No shared access signatures are needed; the Terraform `azurerm` backend authenticates via Managed Identity.

#### Choose a [data transfer](https://learn.microsoft.com/en-us/azure/architecture/data-guide/scenarios/data-transfer) technology

Data transfer into Azure uses command-line tools: Azure CLI, AzCopy, or Azure
PowerShell. Physical transfer options (Data Box, Import/Export service) are not
needed — no large-scale bulk migration from on-premises exists. Azure Data
Factory is not needed — the ETL is a single Python script running as a
Kubernetes CronJob with no pipeline orchestration requirement.

#### Candidates evaluated

| Service | Decision | Reason |
|---|---|---|
| Azure Managed Disks — Standard SSD | **Selected — OS disk** | Recommended for web and application servers; cheaper than Premium SSD; usable as an OS disk; compatible with AKS node pool provisioning. |
| Azure Managed Disks — Standard HDD | **Selected — PostgreSQL data disk** | Lowest cost for a non-critical, small-volume persistent volume in a demo project. Planned upgrade to Standard SSD in Q1 2028. |
| Azure Blob Storage | **Selected — Terraform state** | Stores Terraform remote state via the native `azurerm` backend. Standard LRS hot tier; negligible cost for a state file workload. |
| AzCopy / Azure CLI / Azure PowerShell | **Selected — data transfer** | Free command-line tools for scripted data transfer. Sufficient for all data movement this project requires. |
| Azure Managed Disks — Premium SSD | Rejected | Production-grade, low-latency block storage for mission-critical workloads; higher cost with no performance benefit for a small demo project. |
| Azure Managed Disks — Premium SSD v2 | Rejected | Adjustable IOPS and throughput for production databases; no performance tuning requirement exists for this workload. |
| Azure Managed Disks — Ultra Disk | Rejected | NVMe-based storage for SAP HANA and high-transaction workloads; cannot be used as an OS disk; not applicable. |
| Azure Elastic SAN | Rejected | Cloud-native SAN over iSCSI for consolidating block storage across multiple VMs; no multi-VM shared storage or SAN migration requirement. |
| Azure Container Storage | Rejected | Managed persistent volume orchestration for AKS; adds managed-service cost and complexity. The native AKS storage class with managed disks handles a single PostgreSQL PVC adequately. |
| Azure Files | Rejected | SMB/NFS cloud-native file shares; no shared file system requirement exists. PostgreSQL uses a block (ReadWriteOnce) PVC. |
| Azure NetApp Files | Rejected | Enterprise high-performance NFS/SMB for SAP, HPC, and large-scale file workloads; not applicable. |
| Azure Managed Lustre | Rejected | Distributed parallel file system for HPC workloads; not applicable. |
| Data Lake Storage Gen2 | Rejected | Big data analytics object storage built on Blob Storage; not applicable. |
| Azure Data Box / Import/Export service | Rejected | Physical hardware for bulk data migration where network transfer is impractical; no large-scale on-premises migration exists. |
| Azure Data Factory | Rejected | Managed ETL orchestration for complex multi-source pipelines; not needed. The ETL is a single Python script running as a Kubernetes CronJob. |

### Choose a data store

DineSafeViz stores structured, relational data — normalized inspection records with clear foreign key relationships between establishments, inspections, and infractions — and serves them to two read clients: a Flask web app and a Grafana dashboard. The decision tree from [Prepare to choose a data store in Azure](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/data-stores-getting-started) and the model taxonomy in [Understand data store models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models) both lead directly to a relational OLTP store. PostgreSQL is the existing engine. The remaining decision is whether to consume it as a managed Azure PaaS service or run it self-hosted inside the AKS cluster; this section concludes that **self-hosted PostgreSQL on AKS, managed by the [CloudNativePG](https://cloudnative-pg.io/) operator (CNCF Sandbox project)**, is the right fit for this project's budget, scale, and portfolio goals.

The data is structured, schema-on-write, and accessed primarily by joins and filters against a static ~100k-row dataset. Nothing about the workload requires NoSQL flexibility, analytical pre-aggregation, object storage, or full-text indexing.

#### Decision tree path / data model fit

[Understand data store models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models) frames the first question as: what are the workload access patterns? DineSafeViz access patterns are point reads and filtered range queries over normalized relational tables — the textbook fit for a relational store. The heuristic table in that article maps "strict multi-entity transactions" and "complex joins" to relational; DineSafeViz uses both.

[Prepare to choose a data store in Azure](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/data-stores-getting-started) then asks:

1. **What is the data format?** Structured tables with well-defined schema. → relational.
2. **OLTP or OLAP?** OLTP. The [OLTP article](https://learn.microsoft.com/en-us/azure/architecture/data-guide/relational-data/online-transaction-processing) describes managing transactional data with ACID semantics. DineSafeViz does not process live business transactions, but the data characteristics — normalized schema, moderate reads, periodic bulk-load writes from the ETL — match the OLTP profile far better than OLAP's star-schema/MPP pattern, which is overkill for a ~100k-row dataset.
3. **Full-text or search index needed?** No. Grafana and Flask query by field value, not free-text relevance.
4. **Relational database technology?** Yes — the codebase targets PostgreSQL via SQLAlchemy.
5. **Managed (PaaS) or self-hosted (IaaS / containerized)?** Self-hosted in AKS. The PaaS path would be Azure Database for PostgreSQL — Flexible Server; it is rejected on cost and portfolio grounds documented below.
6. **What level of control over the OS and engine?** Full control. CloudNativePG runs the engine in pods we own end to end — PVC, config, version, extensions, backup schedule.

#### Is managed Azure Database for PostgreSQL overkill?

For this workload, yes. The decision turns on three factors: cost vs. value delivered, fit with the planned DR strategy, and portfolio narrative.

**Cost comparison (list price, Canada Central, USD, approximate):**

| Option | Monthly cost | Notes |
|---|---|---|
| Azure Database for PostgreSQL — Flexible Server, Burstable B1ms (1 vCore, 2 GB RAM) | ~$12–15 compute + ~$4 storage (32 GiB P4) + backup storage ≈ **$16–20/mo** | No permanent free tier exists for Flexible Server. The Azure free-account 12-month B1ms credit is a one-off; after expiry the workload pays full pay-as-you-go rates. |
| Self-hosted PostgreSQL container in AKS, 32 GiB Standard HDD PVC | $0 incremental compute (rides existing AKS node) + ~$1.54/mo for PVC + ~$0.05/GiB/mo for snapshots ≈ **~$2–3/mo** | The AKS node pool is already provisioned for Flask, Grafana, and ingress; PostgreSQL fits in the same node's headroom for this workload. |
| **Delta** | **~$15/mo (~$180/yr)** | Modest absolute cost; significant for a personal homelab budget and worth re-evaluating at each renewal. |

List prices are estimates and should be verified against the Azure pricing calculator at provisioning time; reservations and regional pricing can shift these by 10–30%.

**Value the managed service would add that this project does not need:**

- **Automated patching, monitoring, and engine upgrades** — useful in production, but these are exactly the operations the portfolio is intended to demonstrate.
- **Zone-redundant HA and cross-region geo-replication** — paid add-ons; this is a single-region demo with a custom DR plan (see roadmap below).
- **7-day automated point-in-time restore** — replaced by the explicit nightly snapshot plus GitHub Actions cross-region replication described below.

**Portfolio rationale:** the target role for this repo is sysadmin / DevOps. Managing a stateful Kubernetes workload — an operator-managed PostgreSQL with WAL archiving, scheduled snapshots, restore drills, and a documented failover runbook — directly showcases the operations work an employer wants to see. Outsourcing that work to a PaaS removes the showcase.

**Conclusion:** managed Azure Database for PostgreSQL is over-engineered for the data volume, costs roughly an order of magnitude more than self-hosting, and removes the very operational surface this portfolio is meant to demonstrate.

#### Best practices for self-hosted PostgreSQL on AKS

The deployment uses the [CloudNativePG](https://cloudnative-pg.io/) Kubernetes operator. CloudNativePG is the modern best-in-class community choice for production PostgreSQL on Kubernetes: it manages StatefulSets, streaming replication, scheduled physical base backups, continuous WAL archiving to object storage, declarative failover, and rolling minor-version upgrades, all through a small set of custom resources (`Cluster`, `ScheduledBackup`, `Backup`).

| Concern | Practice |
|---|---|
| Workload definition | A CloudNativePG `Cluster` custom resource. Single instance for v0.4; scale to two instances for streaming replication once node headroom permits. |
| Storage | `ReadWriteOnce` PVC on Azure Managed Disk (Standard HDD per the storage section); `fsGroup` set on the pod for data-directory permissions. |
| Resource sizing | Explicit CPU and memory requests and limits on the postgres container; `shared_buffers`, `work_mem`, and `max_connections` tuned for the node size, not left at defaults. |
| Identity and secrets | Database superuser and application user credentials stored in Azure Key Vault, surfaced via the [Secrets Store CSI driver](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver). No secrets in Git. |
| TLS in transit | Cluster-internal TLS issued by `cert-manager`, even for traffic that never leaves the cluster. |
| Encryption at rest | Microsoft-managed-key encryption on the underlying Managed Disk (default); encryption at host enabled on the AKS node pool (per the storage section). |
| Continuous backup | CloudNativePG continuous WAL archiving to an Azure Blob container via `barmanObjectStore`, enabling point-in-time restore. |
| Periodic backup | A `ScheduledBackup` resource for a daily physical base backup at 02:00 local time, after the 00:30 ETL CronJob completes. |
| Network policy | `NetworkPolicy` restricting PostgreSQL pod ingress to the Flask, Grafana, and ETL service accounts only. |
| Observability | `postgres_exporter` sidecar feeding the future Prometheus stack on the self-hosted observability VMs. |

#### Backup and disaster recovery roadmap

The DR design target is **active-passive failover** from a single primary region to a passive DR region, with manual cutover and near-zero cost at rest. Working targets: **RPO ≤ 24 h**, **RTO ≈ 20–30 minutes** (AKS provisioning + restore + DNS TTL). Out of scope for v0.4; planned for the backup-and-DR phase.

**Daily cycle (primary region):**

1. **00:30** — ETL CronJob runs in AKS, pulling any new records that the City of Toronto has published and loading them into PostgreSQL.
2. **02:00** — `ScheduledBackup` triggers CloudNativePG to take a physical base backup against the WAL archive in Azure Blob Storage (primary region). Continuous WAL archiving keeps the recovery window fresh between base backups.
3. **02:15** — A scheduled GitHub Actions workflow runs `az storage blob copy` (or `azcopy sync`) to replicate the previous night's base backup and WAL segments from the primary-region storage account to a DR-region storage account.

**DR-region steady state:**

- Terraform code for the DR AKS cluster, networking, and CloudNativePG installation lives in the repo but is not applied. No compute cost at rest.
- The DR-region storage account holds the latest replicated backup. Storage cost only — Standard LRS hot tier at ~$0.02/GiB/mo plus per-operation charges on the nightly copy.

**Failover runbook (manual):**

1. Confirm primary-region outage and decide to cut over.
2. `terraform apply` the DR-region AKS cluster, networking, and CloudNativePG installation.
3. Bootstrap a new CloudNativePG `Cluster` with `bootstrap.recovery` pointing at the replicated WAL archive in the DR Blob container. The operator restores from the most recent base backup and replays WAL up to the latest available segment.
4. Deploy the Flask app and Grafana to the DR AKS cluster.
5. Update DNS records at the DNS provider to point at the DR ingress IP. Note expected propagation time given the configured TTL.
6. Verify with smoke tests; mark cutover complete.

**Failback** is a separate planned operation once the primary region is restored: rebuild primary AKS, restore from DR backups, switch DNS back, decommission the DR-region compute.

The at-rest cost of this DR posture is essentially the DR-region storage account. No standby compute, no managed-service replica fees, no cross-region peering charges.

#### Candidates evaluated

| Service | Decision | Reason |
|---|---|---|
| Self-hosted PostgreSQL on AKS — CloudNativePG operator | **Selected** | Zero incremental compute cost (rides the existing AKS node pool); operator provides StatefulSet management, streaming replication, WAL archiving to Blob, scheduled physical backups, declarative failover, and rolling minor-version upgrades; aligns directly with the snapshot + GitHub Actions cross-region DR plan; showcases stateful Kubernetes operations for the portfolio. CNCF Sandbox governance and active community. |
| Self-hosted PostgreSQL on AKS — Bitnami Helm chart | Rejected | Simplest install but no built-in HA, replication, or PITR — every operational concern would be wired up by hand. CloudNativePG offers comparable deploy-time simplicity with materially better operational features. |
| Self-hosted PostgreSQL on AKS — Zalando postgres-operator / Crunchy PGO | Rejected | Production-grade alternatives to CloudNativePG with comparable feature sets. No technical disqualifier; CloudNativePG was chosen for its lighter footprint and CNCF Sandbox governance. |
| Azure Database for PostgreSQL — Flexible Server | Rejected | Managed PaaS PostgreSQL. List price ~$16–20/mo (Burstable B1ms + 32 GiB storage + backup storage) versus ~$2–3/mo for self-hosting — roughly an order of magnitude more for a workload this small. No permanent free tier. Hides the operational surface (backups, snapshots, replication, failover) that this portfolio is intended to demonstrate. Geo-redundant backups and cross-region read replicas are paid add-ons that would replace the planned snapshot + GitHub Actions DR design. Overkill for a ~100k-row, low-traffic, read-mostly dataset. |
| Azure SQL Database | Rejected | SQL Server engine; requires driver and dialect changes in SQLAlchemy and Grafana; no cost or capability advantage over PostgreSQL for this workload. |
| Azure Cosmos DB | Rejected | Document / multi-model NoSQL; adds schema-on-read complexity and loses relational joins for a dataset that is inherently normalized and relational. |
| Azure Managed Redis | Rejected | In-memory key-value store; appropriate for caching, not for the primary data store. Could be revisited as a query cache layer if read latency becomes a concern. |
| Azure Data Explorer | Rejected | Optimized for high-ingest telemetry and time-series logs; the inspection dataset is neither high-velocity nor append-only time-series. |
| Azure AI Search | Rejected | Full-text search index; no free-text search requirement exists. Per [Choose a search data store](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/search-options), PostgreSQL's built-in full-text search would suffice if a search requirement ever emerges. |
| Azure Blob Storage / Data Lake Storage Gen2 | Rejected | Object stores for unstructured or bulk analytical data. [Choose a data storage technology](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/data-storage) positions these for big data ingestion and analytics pipelines, not as the serving layer for a web app. |
| Microsoft Fabric / OneLake | Rejected | Enterprise analytics SaaS platform; appropriate for organization-wide BI with petabyte-scale data. A ~100k-row inspection table routed through a Fabric warehouse would be significant over-engineering. |

#### Notes on tangential sub-articles

**[Data lake scenarios](https://learn.microsoft.com/en-us/azure/architecture/data-guide/scenarios/data-lake):** A data lake is designed for raw, schema-on-read storage of massive and diverse datasets feeding downstream analytics or ML pipelines. DineSafeViz has a small, stable, structured dataset with no ML pipeline and no raw-to-curated transformation layer. The data lake pattern does not apply.

**[Choose a pipeline orchestration technology](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/pipeline-orchestration-data-movement):** Azure Data Factory, Fabric Data Factory, SSIS, and Apache Oozie are the candidates. The DineSafeViz ETL is a lightweight Python script that fetches the DineSafe open data feed and bulk-loads it into PostgreSQL on a schedule. That script runs as a Kubernetes CronJob. A managed orchestration service like ADF would add cost and operational surface area (the free tier does not cover production-grade activity volumes) with no benefit over a CronJob for a single-source, single-destination batch load. This article is noted for future reference if the ETL grows to multiple sources or requires retry orchestration, branching logic, or SLA monitoring.

**[Choose a search data store](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/search-options):** Azure AI Search and Elasticsearch both require maintaining a separate index synchronized with the primary database. No user-facing free-text search exists in DineSafeViz. SQL full-text search in PostgreSQL would be the first option if a search requirement ever emerges; a dedicated search index is not warranted.

### Choose an analytics solution

DineSafeViz uses Grafana, running as a container in AKS, to visualize inspection data stored in PostgreSQL. That is the full extent of the analytics requirement: a dashboarding tool that reads from a relational database. No data warehouse, no batch pipeline, and no streaming ingestion exist in this stack.

The Microsoft guidance on [analytical data stores](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/analytical-data-stores) and [analysis, visualizations, and reporting](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/analysis-visualizations-reporting) is written for big data architectures with serving layers, hot/cold paths, and Lambda-style pipelines. None of those patterns apply here. Grafana's built-in PostgreSQL data source handles the query layer directly; no intermediate analytical store sits between the database and the visualization.

#### Decision tree path

Following the key selection criteria from the analytical data stores article:

1. Do you need a hot-path serving layer separate from your operational database? **No** — Grafana queries PostgreSQL directly.
2. Do you need massively parallel processing or query scale-out? **No** — the dataset is a single city's inspection records; volume is small.
3. Do you prefer a relational data store? **Yes** — PostgreSQL is already chosen; no additional store is needed.
4. Do you collect time-series or append-only data requiring a specialist store? **No** — inspection records are relational, low-volume, and updated in place.

Following the key selection criteria from the analysis and reporting article:

1. Do you need to connect to hundreds of data sources and centralize reporting across a domain? **No** — one PostgreSQL database.
2. Do you need embedding capabilities? **Yes** — the Grafana dashboard is embedded in the web app via iframe.
3. Do you need offline capabilities? **No**.
4. Do you need a managed cloud visualization service? **No** — Grafana runs self-hosted in the AKS cluster, which keeps costs at zero.

Conclusion: PostgreSQL serves as both the operational database and the analytical data store. Grafana handles all visualization. No additional Azure analytics service is required.

#### Candidates evaluated

| Service | Decision | Reason |
|---|---|---|
| Grafana (self-hosted in AKS) | **Selected** | Open-source; runs in the existing AKS cluster; native PostgreSQL data source; embeds in the web app via iframe; zero additional cost. |
| Power BI | Rejected | Paid SaaS (free tier lacks embedding without licensing); adds an external dependency for a problem already solved by Grafana. |
| Jupyter / Zeppelin notebooks | Rejected | Interactive data science tools for exploration and model development, not operational dashboards. Not applicable to this use case. |
| Microsoft Fabric (Lakehouse, Warehouse, Eventhouse) | Rejected | Enterprise-scale unified analytics platform; requires moderate-to-large data volumes to justify cost and complexity. The [Fabric analytical data stores](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/fabric-analytical-data-stores) decision tree leads to SQL Database at small volumes with structured data — which is already covered by PostgreSQL. |
| Azure Analysis Services | Rejected | Tabular semantic model layer for OLAP queries over large datasets; no SQL language support; not applicable to a small relational dataset. |
| Azure Cosmos DB | Rejected | Document/key-value/graph store for high-throughput NoSQL workloads; no fit for a relational inspection dataset with no scale requirement. |
| Azure Databricks | Rejected | Spark-based platform for big data engineering and ML pipelines; significant cost and operational overhead with no applicable workload here. |

#### Notes on tangential sub-articles

**[Batch processing](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/batch-processing)** covers Microsoft Fabric and Azure Databricks for processing large volumes of data in scheduled jobs. Batch processing assumes a pipeline that transforms raw data before serving it. DineSafeViz has no such pipeline — the application ingests and stores inspection data directly into PostgreSQL, and Grafana reads it. Not applicable.

**[Stream processing](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/stream-processing)** covers real-time event ingestion through services like Event Hubs, Stream Analytics, and Fabric eventstreams. Stream processing applies to high-velocity, continuous data sources such as IoT sensors or application logs. The DineSafe dataset is a periodic batch feed from Toronto Public Health; there is no continuous stream to process. Not applicable.

### Choose an AI service

Not applicable.

### Choose a networking service

AKS handles routing within the cluster, but every public-facing deployment still needs a decision about how traffic enters from the internet. The [Azure load-balancing overview](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/load-balancing-overview) covers six services (API Management, Application Gateway, Application Gateway for Containers, Azure Front Door, Load Balancer, Traffic Manager) and provides a decision tree to narrow the choice. For DineSafeViz the answer is to use none of them as a standalone service: AKS with an nginx ingress controller satisfies all routing requirements inside the cluster, and the explicit preference is to avoid a separate load balancer to contain cost.

#### Decision tree path

The load-balancing decision tree starts with two questions: is this an HTTP(S) application, and is it internet-facing?

1. **HTTP(S) web application?** Yes — Flask and Grafana both serve HTTP.
2. **Internet-facing?** Yes — the app is public.
3. **Global / multi-region?** No — single-region deployment.
4. **Hosting type?** AKS.

For a single-region, internet-facing HTTP workload on AKS the decision tree points to Application Gateway (regional Layer-7 proxy) or Application Gateway for Containers (Layer-7 ingress native to Kubernetes). Both are ruled out on cost grounds. The nginx ingress controller deployed inside AKS performs the same Layer-7 routing (host/path-based rules, TLS termination) and is free and open-source. An Azure Load Balancer standard SKU is still provisioned automatically by AKS when the ingress controller's `Service` type is `LoadBalancer`, but this is a cluster-internal implementation detail rather than a separately managed load-balancing service.

#### Candidates evaluated

| Service | Decision | Reason |
|---|---|---|
| Azure Load Balancer | Not applicable as a standalone service | AKS provisions one automatically for the nginx ingress controller `Service`; it is not configured or managed separately as part of this design. |
| Application Gateway | Rejected | Regional Layer-7 proxy; overlaps with nginx ingress and adds cost without meaningful benefit for a single-region, single-cluster deployment. |
| Application Gateway for Containers | Rejected | Kubernetes-native Layer-7 ingress built on Application Gateway; functionally equivalent to nginx ingress for this workload but carries a managed-service cost. |
| Azure Front Door | Rejected | Global CDN and load balancer; designed for multi-region or acceleration use cases. Single-region deployment; not applicable. |
| Traffic Manager | Rejected | DNS-based global traffic distribution; only relevant for multi-region failover or routing. Not applicable. |
| API Management | Rejected | API gateway product, not a general-purpose load balancer. No API gateway requirement exists. |
| nginx ingress controller (in-cluster) | **Selected** | Free, open-source, widely adopted Kubernetes ingress controller. Handles host/path routing, TLS termination, and upstream selection inside the AKS cluster without a separate billable Azure networking service. |

#### Note on virtual network peering

The [virtual network peering reference architecture](https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/hybrid-networking/virtual-network-peering) covers connecting two or more Azure virtual networks — either within a region or across regions — and spoke-to-spoke communication patterns in hub-and-spoke topologies. DineSafeViz is a single-region deployment with one AKS cluster, one virtual network, and no on-premises connectivity, cross-region peering, or hub-and-spoke topology. Virtual network peering is not applicable to this deployment.

### Choose a messaging service

Not applicable.

### Choose an integration and automation service

Azure offers four overlapping services for integration and automation: Power Automate, Logic Apps, Azure Functions, and WebJobs. None of them are needed for DineSafeViz. The project has no event-driven workflows, no SaaS connector integrations, and no background job scheduling requirements. CI/CD — the only automation this project requires — is already handled by GitHub Actions.

[Integration and automation platform options in Azure](https://learn.microsoft.com/en-us/azure/azure-functions/functions-compare-logic-apps-ms-flow-webjobs) describes these four services as tools for solving integration problems and automating business processes. All four are triggered by events, schedules, or connectors, and all target use cases that are absent from DineSafeViz's scope.

#### Candidates evaluated

| Service | Decision | Reason |
|---|---|---|
| Power Automate | Not applicable | A no-code/low-code workflow tool for office workers and citizen developers integrating SaaS applications. DineSafeViz has no SaaS connectors, no approval flows, and no business process automation needs. |
| Azure Logic Apps | Not applicable | A designer-first workflow integration platform for connecting services and automating multi-step processes. No integration workflows of any kind exist in this project. |
| Azure Functions | Not applicable | Serverless event-driven compute. Already evaluated and rejected in the compute section; DineSafeViz serves HTTP pages continuously and has no function-trigger use cases. |
| Azure App Service WebJobs | Not applicable | Background task runner attached to an App Service web app. The project does not use App Service, and there are no background processing requirements. |


## Appendix

### Consulted Articles

The following articles from [Technology choices for Azure solutions](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/technology-choices-overview) were consulted.