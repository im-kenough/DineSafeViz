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

### Choose a data store

DineSafeViz stores structured, relational data — normalized inspection records with clear foreign key relationships between establishments, inspections, and infractions — and serves them to two read clients: a Flask web app and a Grafana dashboard. The decision tree from [Prepare to choose a data store in Azure](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/data-stores-getting-started) and the model taxonomy in [Understand data store models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models) both lead directly to a relational OLTP store. PostgreSQL is the existing engine, and Azure Database for PostgreSQL — Flexible Server is the managed lift for it in Azure.

The data is structured, schema-on-write, and accessed primarily by joins and filters against a static ~100k-row dataset. Nothing about the workload requires NoSQL flexibility, analytical pre-aggregation, object storage, or full-text indexing.

#### Decision tree path / data model fit

[Understand data store models](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models) frames the first question as: what are the workload access patterns? DineSafeViz access patterns are point reads and filtered range queries over normalized relational tables — the textbook fit for a relational store. The heuristic table in that article maps "strict multi-entity transactions" and "complex joins" to relational; DineSafeViz uses both.

[Prepare to choose a data store in Azure](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/data-stores-getting-started) then asks:

1. **What is the data format?** Structured tables with well-defined schema. → relational.
2. **OLTP or OLAP?** The [OLTP article](https://learn.microsoft.com/en-us/azure/architecture/data-guide/relational-data/online-transaction-processing) defines OLTP as managing transactional data with strong ACID consistency and supporting queries on that data. DineSafeViz does not process live business transactions, but its data characteristics — normalized schema, moderate reads, occasional bulk-load writes from the ETL — match the OLTP profile far better than OLAP. The [OLAP article](https://learn.microsoft.com/en-us/azure/architecture/data-guide/relational-data/online-analytical-processing) describes OLAP as heavy-read aggregations over historical data using star schemas, cubes, or MPP engines; the inspection dataset is too small and the queries too simple to justify that overhead.
3. **Full-text or search index needed?** No. Grafana and Flask query by field value, not free-text relevance.
4. **Relational database technology?** Yes — the codebase already targets PostgreSQL via SQLAlchemy. Azure Database for PostgreSQL is the natural managed target.
5. **PaaS or IaaS?** PaaS. There is no requirement for OS-level access or custom engine configuration that would force IaaS.

#### Candidates evaluated

| Service | Decision | Reason |
|---|---|---|
| Azure Database for PostgreSQL — Flexible Server | **Selected** | Managed PaaS PostgreSQL; zero engine migration cost; free tier (Burstable B1ms, 32 GB storage) fits a portfolio project; supports the existing SQLAlchemy connection string and Grafana PostgreSQL data source with no driver changes. |
| Azure SQL Database | Rejected | SQL Server engine requires driver and dialect changes in SQLAlchemy and Grafana; no cost or capability advantage over managed PostgreSQL for this workload. |
| Azure Cosmos DB | Rejected | Document / multi-model NoSQL; adds schema-on-read complexity and loses relational joins for a dataset that is inherently normalized and relational. |
| Azure Managed Redis | Rejected | In-memory key-value store; appropriate for caching, not for the primary data store. Could be revisited as a query cache layer if read latency becomes a concern. |
| Azure Data Explorer | Rejected | Optimized for high-ingest telemetry and time-series logs; the inspection dataset is neither high-velocity nor append-only time-series. |
| Azure AI Search | Rejected | Full-text search index; no free-text search requirement exists. Noted in [Choose a search data store](https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/search-options): SQL Database's built-in full-text search would suffice if ever needed. |
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