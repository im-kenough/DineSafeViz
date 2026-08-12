# Azure Design Planning

Planning the deployment of DineVizSafe into Azure adopts applicable parts of the [Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework?source=recommendations).

## Pillars

DineVizSafe will optimize for Operational Excellence pillar while operating within the context of a personal portfolio demonstration project

Show all 5 pillars in a chart. have a column describing it. in the pillar column, put a check mark for Operational Excellence.

The app will also focus on

 	OE:05 	Use a standardized infrastructure as code (IaC) approach to prepare resources and configurations. Use IaC to ensure consistent styles, modularization, and quality assurance. Prefer declarative over imperative approaches when practical.

OE:06 	Build a workload supply chain that drives changes through predictable, automated pipelines. Ensure these pipelines test and promote changes across all environments and quality gates. Incorporate comprehensive testing.

OE:07 	Design a monitoring stack that captures operational telemetry, metrics, and logs from the workload's infrastructure and code to validate design decisions and guide future improvements.

## Design Pattern

The [Azure Well-Architected operational excellence design patterns](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/design-patterns) article lists 15 industry patterns that address common operational challenges in cloud workloads. Seven of them apply directly to deploying DineSafeViz on AKS.

### Applicable patterns

| Pattern | How it applies to DineSafeViz on AKS |
|---|---|
| [Compute Resource Consolidation](https://learn.microsoft.com/en-us/azure/architecture/patterns/compute-resource-consolidation) | Flask, Grafana, the ETL CronJob, and self-hosted PostgreSQL all run on a shared AKS node pool. One cluster, one management surface, one set of operational tooling. |
| [Deployment Stamps](https://learn.microsoft.com/en-us/azure/architecture/patterns/deployment-stamp) | Each release is a versioned unit of Helm charts and Terraform — the same stamp can be applied to the primary region or used to provision the cold DR AKS cluster without manual configuration. Supports the active-passive DR strategy. |
| [External Configuration Store](https://learn.microsoft.com/en-us/azure/architecture/patterns/external-configuration-store) | Application configuration is externalized from container images via Kubernetes ConfigMaps. Secrets (PostgreSQL credentials, Key Vault references) are surfaced via the Secrets Store CSI driver — no credentials in Git or baked into images. Environment-specific values can change without rebuilding images. |
| [Gateway Offloading](https://learn.microsoft.com/en-us/azure/architecture/patterns/gateway-offloading) | The nginx ingress controller handles TLS termination at the cluster edge. Individual pods (Flask, Grafana) serve plain HTTP internally; TLS is a gateway concern managed in one place. |
| [Gateway Routing](https://learn.microsoft.com/en-us/azure/architecture/patterns/gateway-routing) | nginx ingress routes traffic by path: `/` → Flask, `/grafana` → Grafana. Adding or changing backends requires only an ingress rule update — pod deployments are unaffected. Both Gateway Routing and Gateway Offloading are satisfied by a single nginx ingress controller. |
| [Health Endpoint Monitoring](https://learn.microsoft.com/en-us/azure/architecture/patterns/health-endpoint-monitoring) | AKS liveness and readiness probes target health endpoints on each pod. Flask exposes a `/health` endpoint; CloudNativePG exposes PostgreSQL readiness via its operator. Kubernetes uses these to restart unhealthy pods and withhold traffic from unready ones — the primary self-healing mechanism for this deployment. |
| [Sidecar](https://learn.microsoft.com/en-us/azure/architecture/patterns/sidecar) | `postgres_exporter` runs as a sidecar container in the PostgreSQL pod. It exposes Prometheus-compatible metrics without modifying the PostgreSQL image or configuration. Observability tooling (the future Prometheus stack) can evolve independently of the database lifecycle. |

### Patterns not applicable to this deployment

The remaining eight patterns are not applicable to DineSafeViz at this stage:

- **Anti-Corruption Layer**, **Strangler Fig** — DineSafeViz is a greenfield build with no legacy system to protect against or migrate away from.
- **Choreography**, **Publisher/Subscriber**, **Messaging Bridge** — the application has no event-driven communication or message broker; the ETL writes directly to PostgreSQL.
- **Gateway Aggregation** — there is no client that needs to aggregate calls to multiple backend services in a single request.
- **Edge Workload Configuration** — this is a single-region, centralized cloud deployment with no edge nodes.
- **Quarantine** — the ETL validates data from the City of Toronto open data feed before loading it, which is the spirit of this pattern, but the implementation is a simple Python script rather than a formal quarantine pipeline. Revisit if the ETL gains multiple external sources or a CI-driven image scanning step.

### Operational Excellence Maturity Model

We will start at Level 1 Operational Excellence and iterate on it.
https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/maturity-model?tabs=level1

---

# Architecture best practices for Azure Kubernetes Service - Operational Excellence
https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service#operational-excellence

Start your design strategy based on the design review checklist for Operational Excellence for defining processes for observability, testing, and deployment. See AKS best practices and Day-2 operations guide to learn about key considerations to understand and implement.

https://learn.microsoft.com/en-us/azure/aks/best-practices
https://learn.microsoft.com/en-us/azure/architecture/operator-guides/aks/day-2-operations-guide


---

https://learn.microsoft.com/en-us/azure/aks/best-practices?source=recommendations

For guidance on a designing an enterprise-scale implementation of AKS, see Plan your AKS design.
https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-start-here?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json

To choose the right cluster mode for your workload and operating model, see AKS Automatic and AKS Standard feature comparison.
https://learn.microsoft.com/en-us/azure/aks/intro-aks-automatic#aks-automatic-and-standard-feature-comparison

https://learn.microsoft.com/en-us/azure/aks/best-practices