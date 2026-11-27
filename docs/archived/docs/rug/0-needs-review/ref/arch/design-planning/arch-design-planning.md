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

---

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

---


## [Technology choices](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/technology-choices-overview) for Azure solutions


### Technology Choices Summary

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
  - Data model: relational OLTP
  - Data store: data store: selfhosted PostgresQL on AKS with CloudNativePG operator
- Analytics Service: future on prem vm monitoring, logging, alerting and observability stack
- AI Service: not applicable
- Networking Service:
  - Nginx Ingress Controller (in cluster)
- Messaging Service: Not applicable
- Integration and automation service:
  - CI/CD: GitHub actions

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

DineSafeViz stores structured, relational data (normalized inspection records) with clear foreign key relationships between establishments, inspections, and infractions. The data is served to two read clients, a Flask web app and a Grafana dashboard. 

DineSafeViz:
- uses the relational OLTP data model
- data store: selfhosted PostgresQL on AKS with CloudNativePG operator

#### Data Model

The [Understand data store models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models) article classifies storage engines into nine models: 
- relational
- document
- column-family
- key-value
- graph
- time-series
- object
- search
- vector

DineSafeViz uses the **relational (OLTP)** model.

DineSafeViz's inspection data is structured, schema-on-write, and organized into normalized tables (`establishments`, `inspections`, `infractions`) with well-defined foreign key relationships. Queries are dominated by filtered joins — reading all infractions for a given establishment, for example — and writes arrive as periodic bulk loads from the ETL CronJob rather than as a continuous high-rate stream. The article's heuristic table maps both "strict multi-entity transactions" and "complex joins" to the relational model; which is  the access patterns DineSafeViz uses.

No other model applies: the dataset is too small and structured for an analytics or OLAP store, there is no free-text search requirement, no high-rate telemetry stream, no graph traversal, and no schemaless document flexibility needed.

#### OLTP Solutions

The [OLTP solutions](https://learn.microsoft.com/en-us/azure/architecture/data-guide/relational-data/online-transaction-processing) article defines OLTP as the management of transactional data — typically business interactions recorded as they occur. DineSafeViz does not process live business transactions (no payments, orders, or inventory movements), but its data characteristics match the OLTP trait profile: highly normalized schema, schema-on-write enforcement, strong consistency, and a mix of bulk writes (ETL) and moderate reads (Flask, Grafana).

##### Workload trait fit

| OLTP trait | DineSafeViz |
|---|---|
| Normalization | Highly normalized — `establishments`, `inspections`, `infractions` |
| Schema | Schema-on-write; enforced by SQLAlchemy models and PostgreSQL constraints |
| Consistency | Strong; ETL loads atomically, readers must see consistent state |
| Integrity | High; foreign key constraints across all three tables |
| Uses transactions | Yes; ETL bulk-loads within a single transaction |
| Locking strategy | Optimistic; single writer (ETL CronJob), multiple read-only clients |
| Updateable | Yes; ETL can update existing records on re-run |
| Appendable | Yes; new inspection records are appended nightly |
| Workload | Moderate reads (Flask page requests, Grafana queries); low-frequency writes (nightly ETL) |
| Indexing | Primary keys; secondary indexes on commonly filtered columns (establishment ID, inspection date) |
| Datum size | Small; each inspection record is a handful of columns |
| Query flexibility | High; SQLAlchemy ORM and raw SQL via Grafana |
| Scale | Small; ~100k rows, growing slowly |

##### Key selection criteria

Azure offers the following OLTP data stores: Azure SQL Database, Azure SQL Managed Instance, SQL Server on Azure VM, Azure Database for MySQL, Azure Database for PostgreSQL, and Azure Cosmos DB. The article's key selection criteria narrow the choice:

- **Do you want a managed service rather than managing your own servers?** No — self-hosted PostgreSQL in AKS via CloudNativePG. A managed service (Azure Database for PostgreSQL — Flexible Server) costs ~$16–20/mo versus ~$2–3/mo self-hosted, and removes the operational surface the portfolio is meant to demonstrate. This eliminates all managed PaaS options.
- **Does your solution have specific dependencies for Microsoft SQL Server, MySQL, or PostgreSQL compatibility?** Yes — PostgreSQL. Flask uses SQLAlchemy with the `psycopg2` driver; Grafana uses its native PostgreSQL data source. Both work equally against a self-hosted instance; no Azure PaaS offering is required. This eliminates Azure SQL Database, SQL Managed Instance, SQL Server on Azure VM, and Azure Cosmos DB.
- **Are your write throughput requirements high?** No. The only writer is the nightly ETL CronJob. In-memory tables and global distribution capabilities are not needed.
- **Is your solution multitenant?** No. Single-tenant personal project; elastic pools and Cosmos DB isolation models do not apply.
- **Does your data need to be readable with low latency in multiple regions?** No. Single-region deployment; Canada Central only.
- **Does your database need to be highly available across geographic regions?** Not for v0.4. DR is a manual active-passive failover to a cold DR region (see the DR roadmap section). Geo-replication and automatic failover are out of scope for now.
- **Does your workload require guaranteed ACID transactions?** Yes. The ETL bulk-load must succeed or fail atomically; partial loads must not be committed. PostgreSQL's MVCC-based transaction model satisfies this requirement natively.
- **Does your database have specific security needs?** Standard needs: encryption at rest and in transit, role-based access (application user vs. superuser), and network isolation via `NetworkPolicy`. No row-level security or data masking is required.
- **Does your solution require distributed transactions?** No. All data lives in a single PostgreSQL instance; no cross-database or cross-service transaction coordination is needed.

**Conclusion:** self-hosted PostgreSQL on AKS, managed by the CloudNativePG operator. The first criterion (cost and portfolio rationale) eliminates all managed PaaS options; the remaining criteria confirm that no advanced scale, multi-region, or distributed-transaction capabilities are required.

#### Prepare to choose a data store in Azure

##### Functional requirements

- **Data format:** Structured tables. Three normalized relational tables — `establishments`, `inspections`, `infractions` — with well-defined schema and foreign key relationships. No semi-structured or unstructured data.
- **Purpose:** OLTP. Periodic bulk-load writes from the ETL CronJob; read-heavy queries from Flask and Grafana. Not OLAP — no star schema, no MPP aggregation, no pre-aggregated cubes needed.
- **Search needs:** None. Queries filter by field value (establishment name, inspection date, infraction severity). No full-text relevance ranking is required.
- **Specialized:** None. No vector embeddings and no graph traversal.
- **Data access method:** Direct SQL. Flask uses SQLAlchemy with the `psycopg2` driver; Grafana uses its native PostgreSQL data source. No proprietary API layer.
- **Data relationships:** Joins. `inspections` joins `establishments`; `infractions` joins `inspections`. No graph traversal or hierarchical structures.
- **Consistency model:** Strong. The ETL bulk-loads new records in a single transaction; Flask and Grafana must read consistent data at all times.
- **Schema flexibility:** Schema-on-write. The DineSafe inspection dataset has a stable, well-defined schema. No schema-on-read flexibility is needed.
- **Concurrency needs:** Low. The ETL CronJob is the only writer; Flask and Grafana are read-only clients. No high-write concurrency or complex locking concern.
- **Data life cycle:** Long-term hot data. Historical inspection records accumulate over time but remain actively queried. No cold or archival tiering is needed at this scale.
- **Data movement:** ETL. A Python CronJob extracts records from the City of Toronto DineSafe open data feed, transforms them, and loads them into PostgreSQL. No ELT or pipeline orchestration is required.

##### Nonfunctional requirements

- **Latency and throughput:** Batch processing. The ETL runs on a nightly CronJob schedule. Flask and Grafana serve read queries at low traffic volumes. Sub-second query response is sufficient; real-time ingestion is not required.
- **Scalability:** Vertical. The dataset is small (~100k rows) and grows slowly. Upgrading the AKS node is sufficient for the foreseeable future. No global distribution is needed.
- **Reliability and availability:** No formal SLA. This is a personal portfolio project. CloudNativePG provides pod-level self-healing via Kubernetes. DR is a manual active-passive failover with RPO ≤ 24 h and RTO ≈ 20–30 min.
- **Limits:** Well within PostgreSQL defaults. A ~100k-row dataset requires only basic tuning of `shared_buffers`, `work_mem`, and `max_connections`.

##### Cost and management considerations

- **Managed versus self-hosted:** Self-hosted (containerized). PostgreSQL runs in the AKS cluster managed by the CloudNativePG operator. Managed PaaS (Azure Database for PostgreSQL — Flexible Server) costs ~$16–20/mo at list price versus ~$2–3/mo self-hosted and removes the operational surface the portfolio is meant to demonstrate. See the cost comparison table in the section below.
- **Region availability:** Canada Central. No data residency or compliance constraint beyond keeping data in Canada.
- **Cost optimization:** No tiered storage or caching layer is needed. The PVC is Standard HDD — the cheapest Azure block tier. Queries are infrequent and low-volume enough that a cache layer would add complexity with no measurable benefit.
- **Licensing and portability:** PostgreSQL is open-source (PostgreSQL License) with no vendor lock-in. Although MySQL would be technically sufficient for this workload, PostgreSQL is chosen to showcase enterprise-grade relational database administration. MS SQL is excluded: no perpetual free tier exists and the licensing overhead is not justified for a personal project.

##### Security and governance

- **Encryption:** At-rest encryption is provided by default via Microsoft-managed keys on Azure Managed Disk. Encryption at host is enabled on the AKS node pool. In-transit: cluster-internal TLS is issued by `cert-manager`, even for traffic that never leaves the cluster.
- **Authentication and authorization:** Superuser and application-user credentials are stored in Azure Key Vault and surfaced via the Secrets Store CSI driver. No credentials in Git. AKS Workload Identity (Entra managed identity) authenticates pods to Key Vault.
- **Auditing and monitoring:** PostgreSQL activity logging via the `postgres_exporter` sidecar feeds the future Prometheus stack on the self-hosted observability VMs. Formal audit logging is out of scope for v0.4.
- **Networking:** A `NetworkPolicy` restricts PostgreSQL pod ingress to the Flask, Grafana, and ETL service accounts only. No public endpoint is exposed. No Azure private endpoint is needed — all traffic stays within the AKS cluster virtual network.

##### DevOps and team readiness

- **Skill sets:** PostgreSQL administration, Kubernetes, and Helm. SQLAlchemy for Flask. Grafana's native PostgreSQL data source. CloudNativePG's CRD-based management model — no shelling into the container for routine operations.
- **Client support:** Python (`psycopg2` via SQLAlchemy) and Grafana's native data source both use mature, well-maintained PostgreSQL drivers with no compatibility concerns.
- **Tooling integration:** CloudNativePG integrates with Kubernetes-native tooling (`kubectl`, Helm). Observability feeds into a future Prometheus/Grafana stack on the self-hosted VMs. CI/CD uses GitHub Actions for application deployment and Terraform for infrastructure.

##### Key questions

- **What level of control do you need over the OS and database engine?** Full control. CloudNativePG runs in pods owned end-to-end: PVC, config, version, extensions, and backup schedule. Demonstrating this operational surface is a primary portfolio goal.
- **Will your workloads use a relational database technology?** Yes — PostgreSQL. MySQL would be technically sufficient, but PostgreSQL is chosen to showcase enterprise-grade relational database administration.
- **Will your workloads use SQL Server?** No. MS SQL is excluded on cost and licensing grounds; PostgreSQL meets all requirements at zero licensing cost.
- **Does your Azure solution include Power Platform or Dynamics 365 workloads?** No.
- **Will your workloads use key-value database storage?** No. A Redis cache layer would only be considered if read latency became a concern, which it has not.
- **Will your workloads use document or graph data?** No. The inspection dataset is normalized and relational. No document flexibility or graph traversal is needed.
- **Will your workloads use column-family data?** No.
- **Will your workloads require high-capacity data analytics capabilities?** No. Grafana queries PostgreSQL directly via its native data source. No MPP engine, data warehouse, or OLAP pre-aggregation layer is needed.
- **Will your workloads require search engine capabilities?** No. Queries filter by field value; no full-text relevance search exists in the application.
- **Will your workloads use time-series data?** No. Inspection records are relational and normalized. The inspection date is a filter field, not the primary index dimension.

and the model taxonomy in [Understand data store models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models) both lead directly to a relational OLTP store. PostgreSQL is the existing engine. The remaining decision is whether to consume it as a managed Azure PaaS service or run it self-hosted inside the AKS cluster; this section concludes that **self-hosted PostgreSQL on AKS, managed by the [CloudNativePG](https://cloudnative-pg.io/) operator (CNCF Sandbox project)**, is the right fit for this project's budget, scale, and portfolio goals.

The data is structured, schema-on-write, and accessed primarily by joins and filters against a static ~100k-row dataset. Nothing about the workload requires NoSQL flexibility, analytical pre-aggregation, object storage, or full-text indexing.




##### Candidates evaluated

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

When connecting on prem VMs with AKS, will consider tailscale overlay network.

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