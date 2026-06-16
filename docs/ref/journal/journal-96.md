# Journal 96

## 2026-06-15 — Complete "Choose a compute service" section in arch-design-planning.md

### Context

User asked to work through the Azure Technology Choices article and complete the
"Choose a compute service" section in `docs/ref/arch/arch-design-planning.md`.
The section had sparse, unfinished candidate notes. Three reference articles were
fetched:

- https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree
- https://learn.microsoft.com/en-us/azure/architecture/microservices/design/compute-options
- https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/choose-between-traditional-web-and-single-page-apps

### Decision tree path followed

DineSafeViz is a **greenfield / build-new** workload (not a migration).

1. Full IaaS control needed? → No (want managed services)
2. HPC/batch? → No
3. Event-driven / serverless? → No (serves HTTP pages, not event triggers)
4. Managed web hosting only? → No (want container orchestration showcase)
5. Need container orchestration? → Yes
6. Need direct Kubernetes API / control plane access? → **Yes** → AKS
   (Container Apps abstracts away the K8s API, defeating the portfolio purpose)

### Candidates evaluated and outcome

| Service | Outcome | Reason |
|---|---|---|
| Azure Virtual Machines | Rejected | IaaS; full OS management overhead; no container orchestration showcase |
| Azure App Service | Rejected | PaaS web hosting only; no K8s or container orchestration; suitable style is web-queue-worker, not N-tier |
| Azure Functions | Rejected | FaaS / event-driven; no fit for a traditional page-serving web app |
| Azure Kubernetes Service | **Selected** | Managed K8s; exposes control plane; widely used enterprise tool for DevOps showcase |
| Azure Container Apps | Rejected | Managed service built on K8s but hides the K8s API; reduces demonstration value |
| Azure Container Instances | Rejected | Single-container execution only; no orchestration; defeats DevOps showcase purpose |
| Azure Red Hat OpenShift | Rejected | Not applicable — no OpenShift requirement |
| Azure Batch | Rejected | Not applicable — HPC/parallel processing workload |
| Azure VMware Solution | Rejected | Not applicable — VMware workload only |

### Traditional web app vs SPA decision

Per the Microsoft article, DineSafeViz qualifies as a traditional web app on all criteria:
- Client-side requirements are read-only (inspections table, stats, dashboard iframe)
- No auth wall → public-facing; benefits from search engine indexing
- No rich interactive forms or complex client-side state
- No existing web API being exposed to other clients

A SPA would be overkill. Blazor is also not relevant (not a .NET project).

### Files changed

- `docs/ref/arch/arch-design-planning.md` — expanded "Choose a compute service"
  section with decision tree path, candidate evaluation table, and completed the
  Traditional Web App vs SPA subsection. Also added analysis stub to the
  "Choose a container option" section.

---

## 2026-06-15 — Complete "Choose a hybrid service" section

### Context

User asked to complete the hybrid section, providing four reference articles and
clarifying the full stack topology:

- App: AKS on Azure
- CI/CD: GitHub Actions (SaaS)
- Container images: ACR (Azure)
- Observability: self-hosted VMs *(planned)* for Grafana, Prometheus, Uptime
  Kuma, Alertmanager, etc. — running outside Azure

The initial draft treated the app as pure cloud with no hybrid footprint. The
self-hosted monitoring VMs change that — they are existing/custom VM workloads
that sit outside Azure, which is exactly the scenario the hybrid decision tree
addresses.

### Key decision: Azure Arc-enabled servers

Following the decision tree:
- Hardware: existing/custom → server-class hardware (not IoT edge devices)
- Workload: VM-based Linux servers
- → Azure Arc-enabled servers

Arc installs a lightweight agent and projects the VMs into Azure Resource
Manager. This gives Azure Monitor, Defender for Cloud, Azure Policy, and portal
inventory coverage over the self-hosted machines — a unified operations plane
alongside the AKS cluster.

Deferred to the monitoring phase. Not in scope for the initial AKS deployment.

### Articles read

- https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/hybrid-considerations
- https://learn.microsoft.com/en-us/azure-stack/user/azure-stack-considerations
- https://learn.microsoft.com/en-us/azure/azure-local/concepts/compare-windows-server
- https://learn.microsoft.com/en-us/windows-server/storage/storage-spaces/choose-drives

### Files changed

- `docs/ref/arch/arch-design-planning.md` — rewrote "Choose a hybrid service"
  section with updated stack context, decision tree path, full candidate table,
  and note on the choose-drives sub-article.
