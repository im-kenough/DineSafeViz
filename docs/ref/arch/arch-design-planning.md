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

### Choose a compute service

Q: What compute service do I choose?

A: AKS

This app will use Azure Kubernetes Service.

[Considerations](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree)

![Choose AKS](/docs/img/choose-aks.png)

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

**Azure Container Apps** is the closest alternative. It is a managed service
built on top of Kubernetes and provides Dapr integration, per-app scaling, and
scale-to-zero out of the box. However, it does not expose the Kubernetes API or
control plane. For a DevOps portfolio project the hands-on K8s surface is the
point, so Container Apps is ruled out.

**Azure Container Instances** can run the application image directly and is the
simplest path to a running container in Azure. It has no orchestration, no
scheduling, and no built-in health management. It is useful for one-off or
sidecar workloads but not suitable here.

**Kubernetes at the edge** (Arc-enabled K8s, etc.) is not applicable — this is
a single-region cloud deployment.



### Choose a hybrid service

### Choose a data store

### Choose an analytics solution

### Choose an AI service

Not applicable.

### Choose a networking service


### Choose a messaging service

Not applicable.
