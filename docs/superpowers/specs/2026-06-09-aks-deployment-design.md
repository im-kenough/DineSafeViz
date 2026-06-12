# DineSafeViz on Azure AKS — Phase 1 Design Spec

**Date:** 2026-06-09
**Purpose:** Deploy DineSafeViz to Azure Kubernetes Service (AKS) as a
portfolio-grade, lean-budget production environment, with a parallel staging
environment and a forward-compatible path to multi-region disaster recovery.

## Summary

Two separate AKS clusters (prod and staging) in East US 2, sized to a single
availability zone but configured for multi-AZ autoscaling. Both clusters are
**stopped by default** via GitHub Actions workflows; demos and development
sessions bring them up on demand, holding the steady-state cost to ~USD $36/mo
inside the lean tier target of $25-50/mo. Application stack — Flask web,
CloudNativePG-managed Postgres, and the Grafana-based analytics dashboard —
deploys via a single Helm chart with per-environment values overrides.
GitHub Actions authenticates to Azure via OIDC federated identity (no static
secrets), with required-reviewer approval gates on prod deploys via GitHub
Environments. CNPG writes WAL segments and daily basebackups to a GRS-
replicated Azure Blob storage account, pre-positioning a Phase 2 DR cluster in
West US 2 as a configuration change rather than a re-architecture.

## Goals

1. **Operationally excellent** — every Phase 1 decision favors enterprise-
   recognizable patterns (managed identities over secrets, OIDC over PATs,
   Workload Identity over imagePullSecrets, GitHub Environments for approval
   gates, namespaced workload separation, etc.) at the lowest defensible cost.
2. **Lean-budget steady state** — $25-50/mo cap on steady state with cluster
   stop-by-default lifecycle; minimal always-on infrastructure footprint.
3. **Security and privacy first** — least-privilege managed identities per
   pod-class, network policy default-deny, single-tenant Key Vault per
   environment, no static credentials anywhere.
4. **DR-ready by construction** — WAL archive + GRS-replicated blob storage
   enable a Phase 2 DR cluster activation without re-architecting the data
   layer; RPO ≤ 24h / RTO ≤ 4h target.
5. **Comprehensive documentation** — naming convention, account inventory,
   failure modes, runbooks, observability baseline, and roadmap all
   inline in this spec.
6. **Portfolio signal** — a hiring manager reading this design recognizes
   modern AKS practice (Workload Identity, CNPG operator, OIDC federation,
   stop-by-default cost optimization, multi-region readiness).

## Non-goals (Phase 1)

- 24/7 uptime SLA. Site reachable only when cluster manually started.
- Multi-region active-active.
- Application Gateway WAF / Azure Front Door.
- Private AKS API endpoint + Bastion (Phase 2 enhancement).
- In-cluster Prometheus / Loki / monitoring Grafana stack (Phase 2).
- HPA-driven autoscaling under real traffic (Phase 2 + load test).
- PR preview environments (Phase 2).
- GitOps controller (Argo CD / Flux) — Phase 3.

## Decision matrix

| Concern | Choice | Rationale |
|---|---|---|
| Cluster topology | Separate prod + staging clusters | Isolation matches stated security goal; ~$12/mo premium worth the blast-radius story |
| AKS control plane tier | Free | No SLA acceptable for portfolio; saves $73/mo per cluster vs Standard |
| Region | East US 2 (primary), West US 2 (Phase 2 DR) | Cheapest US compute, widest service availability; accept loss of Canada-data-sovereignty story |
| Cluster lifecycle | Stop-by-default via `az aks stop` | Drives steady-state cost down; demonstrates immutable infra + idempotent IaC |
| Node pools | 1× B2s on-demand `syspool` + 1× B2s spot `usrpool` | Stability for system/DB, cost for stateless app |
| Autoscaling | `syspool` 1-2, `usrpool` 1-3, multi-AZ pool definitions | HA-capable infra, idle-cost minimum |
| Database | CloudNativePG (in-cluster) | Free CNCF operator; PITR + DR-ready via barman cloud + Azure Blob |
| Backups | WAL archive + daily basebackup to GRS Azure Blob | Phase 2 DR is config change, not migration |
| RPO / RTO target | ≤ 24h / ≤ 4h | Matches stated "daily sync is sufficient" |
| Storage class | Standard SSD (E10), `Retain` reclaim | Cost-appropriate for our IOPS; `Retain` protects against accidental delete |
| DNS | Azure DNS | Single ecosystem, Terraform-managed records, free DNS-01 challenge via Workload Identity |
| Domain | `dinesafeviz.com` (Namecheap registrar, NS delegated to Azure DNS); staging at `stg.dinesafeviz.com` | Conventional single-TLD + subdomain pattern |
| TLS | cert-manager + Let's Encrypt DNS-01 | Free, k8s-native, works while cluster is stopped (vs HTTP-01) |
| Ingress | NGINX Ingress Controller + Standard LB + static Public IP | Industry default; ~$4/mo per IP vs AGIC's ~$30/mo |
| Image registry | ACR Basic ($5/mo), `AcrPull` via managed identity | No `imagePullSecret`; Workload Identity OIDC for GHA `AcrPush` |
| Secrets | Azure Key Vault (RBAC mode) + CSI Secrets Store Driver | Modern pattern; only externally-sourced secrets stored here (Postgres creds owned by CNPG) |
| IaC | Terraform (Azure provider) + Helm + Helmfile | Terraform for Azure resources, Helm for K8s, Helmfile orchestrates |
| State backend | Azure Storage `stdsvtfsteus2<rnd>` with blob lease locking | Standard enterprise pattern |
| CI/CD identity | GitHub Actions OIDC federated identity (Workload Identity) | No long-lived secrets in GHA; per-env identity scoping |
| CI/CD approval | GitHub Environments (`prod` requires reviewer) | Free on public repos; repo will be made public |
| Network policy | Cilium (built-in AKS option) | Default-deny per namespace; demonstrates modern network security |
| Observability | Container Insights + Azure Monitor alerts | Free/cheap; Prometheus stack lands in Phase 2 |

## Infrastructure overview

### Topology

```
┌──────────────────────────────── Azure subscription ────────────────────────────────┐
│                                                                                    │
│  East US 2 (primary)                          West US 2 (Phase 2 DR)               │
│  ────────────────────                         ─────────────────────                │
│                                                                                    │
│  rg-dsv-shared-eus2                                                                │
│    ├─ ACR (acrdsv<rnd>)                                                            │
│    ├─ DNS Zone (dinesafeviz.com)                                                   │
│    ├─ Storage (tfstate)                                                            │
│    ├─ Log Analytics workspace                                                      │
│    └─ Managed Identities (GHA OIDC)                                                │
│                                                                                    │
│  rg-dsv-prod-eus2                                                                  │
│    ├─ VNet 10.50.0.0/16                                                            │
│    ├─ AKS aks-dsv-prod-eus2 (stopped by default)                                   │
│    │    ├─ syspool: 1× B2s on-demand, zones [1,2,3]                                │
│    │    └─ usrpool: 1× B2s spot, zones [1,2,3]                                     │
│    ├─ Key Vault (kv-dsv-prod-<rnd>)                                                │
│    ├─ Storage Account (stdsvwalprodeus2<rnd>) GRS — CNPG WAL + basebackups         │
│    ├─ Static Public IP (pip-dsv-ingress-prod-eus2)                                 │
│    └─ Workload Identities (CNPG, cert-manager, CSI)                                │
│                                                                                    │
│  rg-dsv-stg-eus2 (parallel structure to prod, smaller PVCs, LRS WAL storage)       │
│                                                                                    │
│  ────────────────────                         ─────────────────────                │
│                                                                                    │
│  Phase 2:                                     rg-dsv-prod-wus2                     │
│                                                 ├─ AKS aks-dsv-prod-wus2           │
│                                                 ├─ Reads same GRS WAL archive      │
│                                                 │  (via -secondary endpoint)       │
│                                                 └─ Replica cluster mode            │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘

  Public traffic:
    dinesafeviz.com      ──Azure DNS──► pip-dsv-ingress-prod-eus2 ──► NGINX ──► dsv-app
    stg.dinesafeviz.com  ──Azure DNS──► pip-dsv-ingress-stg-eus2  ──► NGINX ──► dsv-app
```

## Naming convention

**Pattern:** `<type>-<workload>-<role>-<env>-<region>[-<seq>]`

- `<type>` — Azure CAF abbreviation (`rg`, `aks`, `kv`, `id`, `pip`, `vnet`, `snet`, `nsg`, `log`)
- `<workload>` — `dsv` (DineSafeViz)
- `<role>` — what this resource does (`cnpg`, `certmgr`, `controlplane`, `ingress`, etc.)
- `<env>` — `prod` | `stg` | `shared` | `dr` (Phase 2)
- `<region>` — `eus2` | `wus2`
- `<seq>` — `01`, `02` when multiple

Globally-unique resource types (Storage Accounts, ACR, Key Vault) cannot contain
hyphens (Storage, ACR) or may collide on common names. Names use a collapsed
pattern with a random suffix shown as `<rnd>` (Terraform `random_string` of
length 4, lowercase alphanumeric).

## Full account inventory

### Resource Groups

| Name | Region | Purpose |
|---|---|---|
| `rg-dsv-shared-eus2` | East US 2 | ACR, DNS zone, Terraform state, Log Analytics, GHA Managed Identities |
| `rg-dsv-prod-eus2` | East US 2 | Prod AKS cluster, VNet, Public IP, Key Vault, WAL storage, workload MIs |
| `rg-dsv-stg-eus2` | East US 2 | Staging cluster (parallel structure) |
| `rg-dsv-prod-wus2` | West US 2 | **Phase 2 only** — DR mirror of prod |

### Networking

| Name | Type | CIDR / details |
|---|---|---|
| `vnet-dsv-prod-eus2` | VNet | `10.50.0.0/16` |
| `snet-dsv-aksnodes-prod-eus2` | Subnet | `10.50.0.0/22` |
| `snet-dsv-akspods-prod-eus2` | Subnet | `10.50.4.0/22` (Azure CNI Overlay) |
| `snet-dsv-lb-prod-eus2` | Subnet | `10.50.8.0/24` (reserved for internal LB if added) |
| `vnet-dsv-stg-eus2` | VNet | `10.60.0.0/16` (parallel structure) |
| `pip-dsv-ingress-prod-eus2` | Static Public IP | DNS A `dinesafeviz.com` |
| `pip-dsv-ingress-stg-eus2` | Static Public IP | DNS A `stg.dinesafeviz.com` |
| `nsg-dsv-aksnodes-prod-eus2` | NSG | Default deny + AKS-required rules |
| `nsg-dsv-aksnodes-stg-eus2` | NSG | Same as prod |

### DNS

| Name | Purpose |
|---|---|
| `dinesafeviz.com` (zone in `rg-dsv-shared-eus2`) | Public DNS zone, NS-delegated from Namecheap |

### AKS clusters and node pools

| Name | Region | RG | Tier |
|---|---|---|---|
| `aks-dsv-prod-eus2` | East US 2 | `rg-dsv-prod-eus2` | Free |
| `aks-dsv-stg-eus2` | East US 2 | `rg-dsv-stg-eus2` | Free |
| `aks-dsv-prod-wus2` | West US 2 | `rg-dsv-prod-wus2` | Free (Phase 2) |

Each cluster has identical node pool config:

| Pool | Role | SKU | Mode | Zones | Min | Max |
|---|---|---|---|---|---|---|
| `syspool` | System | Standard_B2s | On-demand | [1, 2, 3] | 1 | 2 |
| `usrpool` | User | Standard_B2s | Spot (cap at on-demand price) | [1, 2, 3] | 1 | 3 |

System pool hosts: NGINX ingress, cert-manager, CNPG operator, CSI driver,
CNPG Postgres pods. User pool hosts: Flask app, analytics dashboard,
init Jobs.

### Azure Container Registry

| Name | Tier | RG |
|---|---|---|
| `acrdsv<rnd>` (e.g., `acrdsv7k2x`) | Basic | `rg-dsv-shared-eus2` |

Repositories: `dinesafeviz/app`, `dinesafeviz/init-db`. The `dinesafeviz/analytics`
slot is reserved; Phase 1 pulls Grafana from `grafana/grafana` upstream.

### Key Vaults

| Name | RG | Mode | Soft-delete | Purge protection |
|---|---|---|---|---|
| `kv-dsv-prod-<rnd>` | `rg-dsv-prod-eus2` | RBAC | 90 days | Enabled |
| `kv-dsv-stg-<rnd>` | `rg-dsv-stg-eus2` | RBAC | 90 days | Enabled |

Secrets per vault: `analytics-admin-password`, `analytics-secret-key`. Other
secrets (Postgres app/superuser creds, TLS cert) are owned by CNPG and
cert-manager respectively.

### Storage Accounts

| Name | RG | Purpose | Redundancy |
|---|---|---|---|
| `stdsvtfsteus2<rnd>` | `rg-dsv-shared-eus2` | Terraform remote state | GRS |
| `stdsvwalprodeus2<rnd>` | `rg-dsv-prod-eus2` | Prod CNPG WAL + basebackups | GRS (replicates to West US 2) |
| `stdsvwalstgeus2<rnd>` | `rg-dsv-stg-eus2` | Staging CNPG WAL | LRS (DR not needed) |

Containers:
- `stdsvtfsteus2<rnd>`: `tfstate` (blobs: `azure-shared.tfstate`, `azure-prod.tfstate`, `azure-staging.tfstate`); `deploy-state` (`prod.json`, `staging.json`).
- `stdsvwalprodeus2<rnd>`: `cnpg-wal-prod`, `cnpg-basebackups-prod`.
- `stdsvwalstgeus2<rnd>`: `cnpg-wal-stg`, `cnpg-basebackups-stg`.

### Managed Identities (User-Assigned)

| Name | RG | Used by | Role assignments |
|---|---|---|---|
| `id-aks-controlplane-prod-eus2` | `rg-dsv-prod-eus2` | AKS prod control plane | `AcrPull` on `acrdsv<rnd>`, `Network Contributor` on prod VNet |
| `id-aks-controlplane-stg-eus2` | `rg-dsv-stg-eus2` | AKS staging control plane | Same, scoped to stg |
| `id-aks-cnpg-prod-eus2` | `rg-dsv-prod-eus2` | CNPG pods (Workload Identity) | `Storage Blob Data Contributor` on `stdsvwalprodeus2<rnd>` |
| `id-aks-certmgr-prod-eus2` | `rg-dsv-prod-eus2` | cert-manager (Workload Identity) | `DNS Zone Contributor` on `dinesafeviz.com` |
| `id-aks-kvcsi-prod-eus2` | `rg-dsv-prod-eus2` | CSI Secrets Store (Workload Identity) | `Key Vault Secrets User` on `kv-dsv-prod-<rnd>` |
| `id-aks-cnpg-stg-eus2` | `rg-dsv-stg-eus2` | Staging CNPG | `Storage Blob Data Contributor` on `stdsvwalstgeus2<rnd>` |
| `id-aks-certmgr-stg-eus2` | `rg-dsv-stg-eus2` | Staging cert-manager | `DNS Zone Contributor` on `dinesafeviz.com` |
| `id-aks-kvcsi-stg-eus2` | `rg-dsv-stg-eus2` | Staging CSI | `Key Vault Secrets User` on `kv-dsv-stg-<rnd>` |
| `id-gha-dsv-prod-eus2` | `rg-dsv-shared-eus2` | GHA prod workflows | `Azure Kubernetes Service Contributor` on `rg-dsv-prod-eus2`, `AcrPush` on ACR |
| `id-gha-dsv-stg-eus2` | `rg-dsv-shared-eus2` | GHA staging workflows | Same, scoped to stg |
| `id-gha-dsv-shared-eus2` | `rg-dsv-shared-eus2` | GHA shared/cross-env workflows | `AcrPush` on ACR, `DNS Zone Contributor` on zone, `Contributor` on shared RG, `Storage Blob Data Contributor` on tfstate |

### Federated identity credentials

Trust GitHub's OIDC issuer (`https://token.actions.githubusercontent.com`) with
audience `api://AzureADTokenExchange`:

| MI | Federated cred name | Subject |
|---|---|---|
| `id-gha-dsv-prod-eus2` | `gha-prod-env` | `repo:im-kenough/DineSafeViz:environment:prod` |
| `id-gha-dsv-prod-eus2` | `gha-prod-tag` | `repo:im-kenough/DineSafeViz:ref:refs/tags/v*` |
| `id-gha-dsv-stg-eus2` | `gha-stg-env` | `repo:im-kenough/DineSafeViz:environment:staging` |
| `id-gha-dsv-stg-eus2` | `gha-stg-pr` | `repo:im-kenough/DineSafeViz:pull_request` |
| `id-gha-dsv-shared-eus2` | `gha-shared-main` | `repo:im-kenough/DineSafeViz:ref:refs/heads/main` |
| `id-gha-dsv-shared-eus2` | `gha-shared-pr` | `repo:im-kenough/DineSafeViz:pull_request` |
| `id-gha-dsv-shared-eus2` | `gha-shared-tag` | `repo:im-kenough/DineSafeViz:ref:refs/tags/v*` |

### Kubernetes namespaces + ServiceAccounts (per cluster)

| Namespace | Purpose | ServiceAccounts (with Workload Identity annotations) |
|---|---|---|
| `kube-system` | AKS-managed | (Azure-managed) |
| `ingress-nginx` | NGINX ingress | `ingress-nginx` (default) |
| `cert-manager` | cert-manager | `cert-manager` (→ `id-aks-certmgr-<env>-eus2`) |
| `cnpg-system` | CNPG operator | `cnpg-manager` |
| `kube-system` (CSI driver) | CSI Secrets Store + Azure provider | `secrets-store-csi-driver` (→ `id-aks-kvcsi-<env>-eus2`) |
| `dsv-app` | Application workloads | `dsv-app`, `dsv-analytics`, `pg-dsv-<env>` (→ `id-aks-cnpg-<env>-eus2`) |
| `dsv-monitoring` | **Phase 2 only** — platform monitoring stack | TBD |

### Logging

| Name | RG | Type | Retention |
|---|---|---|---|
| `log-dsv-shared-eus2` | `rg-dsv-shared-eus2` | Log Analytics workspace | 30 days |

### Tags (applied to every Azure resource)

| Tag | Example value |
|---|---|
| `workload` | `dinesafeviz` |
| `environment` | `prod` \| `stg` \| `shared` |
| `managed_by` | `terraform` |
| `cost_center` | `personal` |
| `owner` | `im-kenough` |
| `repo` | `github.com/im-kenough/DineSafeViz` |

### Account inventory summary

| Account type | Identifier |
|---|---|
| Azure tenant | (created at signup; one tenant, one subscription) |
| Azure subscription | `DineSafeViz` (display name; ID is a GUID) |
| Azure billing account | Personal Microsoft account |
| GitHub account | `im-kenough` |
| GitHub repo | `im-kenough/DineSafeViz` (Phase 1: flip to **public**) |
| GitHub Environments | `prod` (required reviewer), `staging` (auto) |
| Domain registrar | Namecheap |
| DNS provider | Azure DNS (NS-delegated from Namecheap) |
| Container registry | `acrdsv<rnd>.azurecr.io` |
| Postgres app user | `dsv_app` (CNPG-managed) |
| Postgres superuser | `postgres` (CNPG-managed) |
| Analytics admin | `admin` (password in Key Vault as `analytics-admin-password`) |

## Network, DNS, TLS

- **CNI:** Azure CNI Overlay (modern AKS default).
- **Network policy:** Cilium (built-in AKS option).
- **API server access:** Public, IP-allowlisted to workstation + GHA runner ranges
  (Phase 2 enhancement: private AKS API + Bastion).
- **Outbound:** Default AKS-managed LB.
- **Public IP per cluster:** Static, pre-created in Terraform, referenced via
  `loadBalancerIP` on the `ingress-nginx-controller` Service.
- **DNS records:** Terraform-managed A records in Azure DNS zone:
  - `dinesafeviz.com` → prod cluster Public IP
  - `stg.dinesafeviz.com` → staging cluster Public IP
- **NS delegation:** After Azure DNS zone creation, `azurerm_dns_zone.dinesafeviz.name_servers` outputs 4 Azure-assigned NS hostnames. These are configured at Namecheap (Domain → Nameservers → Custom DNS). Propagation can take 24-48h on first delegation; subsequent record changes inside the zone propagate per the record's TTL (~5 min default).
- **TLS:** cert-manager (`ClusterIssuer letsencrypt-prod`) with DNS-01
  challenge via the `azuredns` solver; each cert-manager uses its env's
  Workload Identity (`id-aks-certmgr-<env>-eus2`) to mutate DNS TXT records.
  Renewal: 30 days before expiry, auto. Heartbeat workflow forces monthly
  cluster start to renew certs even during long idle periods.
- **NGINX Ingress:** Installed via Helm chart `ingress-nginx/ingress-nginx` 4.x.
  IngressClass `nginx`. Annotations: `cert-manager.io/cluster-issuer:
  letsencrypt-prod`, `nginx.ingress.kubernetes.io/force-ssl-redirect: "true"`.

## Identity, Secrets, Image Registry

### How GitHub Actions OIDC federation works

The pattern replaces stored Service Principal client secrets with per-run
signed JWT assertions. GitHub runs an OIDC provider at
`https://token.actions.githubusercontent.com`; each workflow run obtains a
short-lived JWT containing claims describing the run (`sub`, `aud`,
`repository`, `ref`, etc.). The workflow exchanges that JWT at Azure AD's STS
endpoint for an Azure access token scoped to a User-Assigned Managed Identity.
Azure AD's federated credential resource maps the JWT's `sub` and `aud`
claims to a specific MI; mismatches fail with `AADSTS70021`.

Result: no long-lived secrets in GitHub Secrets; per-run auditability tying
Azure activity to a specific workflow run; environment-based approval gates
enforced *before* the JWT is even issued.

Workflow requirements:
- `permissions: id-token: write` at job or workflow level.
- `azure/login@v2` action with `client-id`, `tenant-id`, `subscription-id`
  inputs (sourced from `vars.*`, not `secrets.*` — these are not secrets).
- For environment-based subjects: declare `environment: <name>` in the job
  and ensure the environment exists on the repo.

### Image registry

ACR Basic with managed-identity-based pulls: AKS cluster control plane MIs
get `AcrPull` on `acrdsv<rnd>`; pods need no `imagePullSecret`. GHA shared
identity has `AcrPush` for build pipelines.

Image tag conventions:
- `:sha-<7char>` — every build (immutable, primary tag)
- `:<branch-name>` — branch tracking (mutable)
- `:v<semver>` — release tags (immutable)
- `:latest` — main branch HEAD (mutable, *never* used in prod values files)

### Secrets

Azure Key Vault per environment in RBAC mode. Stores only externally-sourced
secrets — Postgres credentials are owned by CNPG (auto-rotated, mounted via
K8s Secrets), TLS certs by cert-manager.

| Secret | Source | Consumer |
|---|---|---|
| `analytics-admin-password` | Terraform `random_password`, written to KV | Analytics Deployment env var |
| `analytics-secret-key` | Terraform `random_password`, written to KV | Analytics Deployment env var |

CSI Secrets Store Driver + `csi-secrets-store-provider-azure` projects KV
secrets as files at `/mnt/secrets-store/` in the consuming pod, optionally
synced to a K8s Secret for env-var consumption.

## Database layer (CloudNativePG)

### Operator

Helm chart `cloudnative-pg/cloudnative-pg` 0.23.x → operator image
`ghcr.io/cloudnative-pg/cloudnative-pg:1.24.x` in namespace `cnpg-system`,
pinned to `syspool` via nodeSelector. Cluster-wide watch scope.

### Per-environment Cluster CR

| Field | Prod | Staging | Phase 2 DR |
|---|---|---|---|
| `metadata.name` | `pg-dsv-prod` | `pg-dsv-stg` | `pg-dsv-prod-dr` |
| `metadata.namespace` | `dsv-app` | `dsv-app` | `dsv-app` |
| `spec.instances` | 1 (Phase 1) → 2 (Phase 2 HA) | 1 | 1 (replica of prod) |
| `spec.imageName` | `ghcr.io/cloudnative-pg/postgresql:17.2-bookworm` | same | same |
| `spec.storage.size` | 32Gi | 16Gi | 32Gi |
| `spec.storage.storageClass` | `dsv-standard-ssd` | same | same |
| `spec.resources.requests.cpu` | 250m | 100m | 250m |
| `spec.resources.requests.memory` | 512Mi | 256Mi | 512Mi |
| `spec.affinity.nodeSelector` | `kubernetes.azure.com/agentpool=syspool` | same | same |
| `spec.affinity.topologyKey` | `topology.kubernetes.io/zone` | same | same |
| `spec.bootstrap.initdb.database` | `dinesafeviz` | `dinesafeviz` | n/a |
| `spec.bootstrap.initdb.owner` | `dsv_app` | `dsv_app` | n/a |
| `spec.bootstrap.recovery.source` | n/a Phase 1 | n/a | `pg-dsv-prod-backup` |
| `spec.replica.enabled` | false | false | true |

### Backup configuration

```yaml
backup:
  barmanObjectStore:
    destinationPath: "https://stdsvwalprodeus2<rnd>.blob.core.windows.net/cnpg-basebackups-prod/"
    azureCredentials:
      inheritFromAzureAD: true   # uses Workload Identity
    wal:
      compression: gzip
      maxParallel: 4
    data:
      compression: gzip
      jobs: 2
  retentionPolicy: "30d"
```

Plus `ScheduledBackup` CR `pg-dsv-prod-daily-backup`, schedule `0 2 * * *`.

### Auto-created Services and Secrets

CNPG creates for each Cluster `<name>`:
- Services: `<name>-rw`, `<name>-ro`, `<name>-r`
- Secrets: `<name>-app`, `<name>-superuser`, `<name>-ca`, `<name>-replication`, `<name>-server`
- ConfigMap: `<name>-monitoring` (Prometheus PodMonitor)
- PVC: `<name>-1` (per instance)

App connects to `pg-dsv-<env>-rw:5432`, reads `pg-dsv-<env>-app` Secret via
`envFrom: secretRef`. The analytics dashboard reads from `pg-dsv-<env>-r`
(any healthy member, primary at Phase 1, prepares for read split when
replicas exist).

### Recovery options

| Scenario | Recovery |
|---|---|
| Postgres pod OOM / crash | CNPG restarts pod automatically; PVC re-mounts |
| PVC corrupted | Patch Cluster CR with `bootstrap.recovery.source: pg-dsv-<env>-backup`; CNPG rebuilds from last basebackup + WAL |
| Region failure (Phase 2) | Promote DR Cluster CR via `replica.enabled: false`; update DNS A record |
| Last-resort (any failure) | Reseed from Toronto Open Data CSVs via `dsv-init-db` Job |

## Helm chart + application deployment

### Repository structure (additions to `infra/`)

```
infra/
├── terraform/
│   ├── azure-shared/     # ACR, DNS, Log Analytics, GHA MIs, federated creds
│   ├── azure-prod/       # prod RG: AKS, VNet, KV, WAL storage, workload MIs
│   ├── azure-staging/    # parallel to azure-prod
│   └── proxmox/          # existing homelab (sandbox; untouched)
├── helm/
│   ├── cluster-bootstrap/  # one-time per cluster (CNPG, ingress, cert-mgr, CSI, StorageClass, ClusterIssuer)
│   └── dinesafeviz/        # the app
└── helmfile.yaml
```

### `dinesafeviz` chart contents (full template inventory)

In namespace `dsv-app` per cluster:

| Kind | Name |
|---|---|
| `ServiceAccount` | `dsv-app`, `dsv-analytics`, `pg-dsv-<env>` |
| `Cluster` (CNPG CR) | `pg-dsv-<env>` |
| `ScheduledBackup` (CNPG CR) | `pg-dsv-<env>-daily-backup` |
| `ConfigMap` | `dsv-pg-init-sql`, `dsv-analytics-datasource`, `dsv-analytics-dashboards` |
| `SecretProviderClass` | `dsv-keyvault-secrets` |
| `PersistentVolumeClaim` | `dsv-analytics-data` (2Gi Standard SSD, Retain) |
| `Deployment` | `dsv-app`, `dsv-analytics` |
| `Service` | `dsv-app` (ClusterIP, port 5000), `dsv-analytics` (ClusterIP, port 3000) |
| `Ingress` | `dsv-app` (host from values), `dsv-analytics` (disabled by default) |
| `Certificate` (cert-manager) | `dsv-app-tls` |
| `NetworkPolicy` | `default-deny-all`, `allow-ingress-to-app`, `allow-app-to-postgres`, `allow-analytics-to-postgres`, `allow-egress-kube-dns`, `allow-egress-azure-blob`, `allow-egress-azuredns`, `allow-egress-acme` |
| `Job` (Helm hooks) | `dsv-init-db` (weight 10), `dsv-init-analytics` (weight 20) |
| `Pod` (Helm test hook) | `dsv-test-connection` |

### Workload placement

| Workload | Node pool | Toleration |
|---|---|---|
| `pg-dsv-<env>` | `syspool` (on-demand) | none |
| `dsv-app` | `usrpool` (spot) | `kubernetes.azure.com/scalesetpriority=spot:NoSchedule` |
| `dsv-analytics` | `usrpool` (spot) | same |
| `dsv-init-db` Job | `usrpool` (spot) | same |
| `dsv-init-analytics` Job | `usrpool` (spot) | same |

### Image tag strategy

| Image | Staging values | Prod values |
|---|---|---|
| `app` | `:sha-<7char>` (set by CI on PR/main) | `:v<semver>` (set by tagged release) |
| `init-db` | mirrors `app` tag | mirrors `app` tag |

Immutable tags only in prod. `:latest` never appears in any `values-prod.yaml`.

### Helmfile orchestration

```yaml
environments:
  prod:
    values:
      - env: prod
      - kubeContext: aks-dsv-prod-eus2
  staging:
    values:
      - env: stg
      - kubeContext: aks-dsv-stg-eus2

releases:
  - name: cluster-bootstrap
    namespace: kube-system
    chart: ./helm/cluster-bootstrap
    values:
      - ./helm/cluster-bootstrap/values-{{ .Values.env }}.yaml

  - name: dsv
    namespace: dsv-app
    chart: ./helm/dinesafeviz
    values:
      - ./helm/dinesafeviz/values-{{ .Values.env }}.yaml
    needs:
      - kube-system/cluster-bootstrap
    set:
      - name: app.image.tag
        value: '{{ env "APP_IMAGE_TAG" | default "" }}'
```

Bootstrap and app deploys: `helmfile --environment <env> sync`.

## GitHub Actions workflows

### Inventory

| Workflow | Trigger | Identity | Purpose |
|---|---|---|---|
| `image-build.yml` | push main / tag v* / PR | `id-gha-dsv-shared-eus2` | Build app + init-db images, push to ACR |
| `terraform-shared.yml` | push main (paths `infra/terraform/azure-shared/**`) | shared | Plan + apply shared infra |
| `terraform-prod.yml` | `workflow_dispatch` (`environment: prod`) | prod | Plan / apply for `azure-prod/` |
| `terraform-staging.yml` | push main + dispatch | staging | Plan / apply for `azure-staging/` |
| `aks-up.yml` | `workflow_dispatch` | env-matched | `az aks start` + helmfile sync |
| `aks-down.yml` | `workflow_dispatch` | env-matched | `az aks stop` |
| `aks-scale.yml` | `workflow_dispatch` | env-matched | `az aks nodepool scale` |
| `app-deploy.yml` | `workflow_dispatch` (manual / chained from image-build for staging) | env-matched | Helmfile sync with specific tag |
| `pr-preview.yml` | `pull_request` | staging | **Phase 2** — per-PR preview |
| `cert-renewal-heartbeat.yml` | scheduled monthly | prod (runs both clusters) | Force cluster start to renew certs |
| `acr-cleanup.yml` | scheduled weekly | shared | Purge untagged ACR images > 30d |
| `db-backup-verify.yml` | scheduled weekly | prod (read-only) | Confirm latest basebackup < 48h old |

### Key workflow patterns

- **`workflow_dispatch` for all sensitive operations** (Terraform apply, app
  deploy to prod, cluster lifecycle). Inputs include typed-confirmation
  strings (e.g., `confirm: STOP-prod`) as a fat-finger safety latch.
- **`environment:` claim on prod-targeting jobs** enables required-reviewer
  approval gate before workflow proceeds. Reviewer is the repo owner.
- **Concurrency:** `aks-${{ inputs.cluster }}` group, `cancel-in-progress:
  false` to prevent overlapping start/stop.
- **State blob `<env>.json`** in `stdsvtfsteus2<rnd>/deploy-state/` records
  current deployed tag. `aks-up.yml` reads it to redeploy the same version
  on a cold start.
- **Reusable composite workflow** `_azure-auth.yml` factors `azure/login@v2`
  for the three identities.

### Pre-prerequisites (one-time setup)

1. Audit git history for any committed secrets:
   `git log -p | grep -iE 'password|secret|key|token'`.
2. Make the repo public: Settings → General → Change visibility.
3. Create GitHub Environments:
   - `prod`: required reviewer = `im-kenough`, deployment branches = `main` + `v*` tags, no wait timer.
   - `staging`: no required reviewer, deployment branches = all.
4. Add repo variables (not secrets):
   - `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
   - `AZURE_CLIENT_ID_PROD`, `AZURE_CLIENT_ID_STAGING`, `AZURE_CLIENT_ID_SHARED`

## Failure modes + runbooks

### Failure mode catalog (abridged; full table in section 7 of design conversation)

Categories covered: compute / nodes (spot eviction, node failure, capacity
exhaustion), database (pod restart, PVC corruption, WAL archive
unreachable, CNPG operator crash), network / ingress (controller crash,
cert-manager failure, LE rate limit, PIP lost, NetworkPolicy self-DoS),
identity / secrets (Workload Identity token failure, ACR pull denied, KV
secret stale), GitHub Actions / CI (OIDC subject mismatch, Terraform state
lock), cost (forgot to stop, spot pricing spike), external (Azure region
outage, Toronto Open Data CSV format change).

Each documented with detection → mitigation → recovery → prevention.

### Runbook index

| ID | Operation | Driver |
|---|---|---|
| RB-01 | Bring up prod for demo | `aks-up.yml cluster=prod` |
| RB-02 | Bring down prod after demo | `aks-down.yml cluster=prod confirm=STOP-prod` |
| RB-03 | Bring up staging for development | `aks-up.yml cluster=staging` |
| RB-04 | Bring down staging | `aks-down.yml cluster=staging confirm=STOP-staging` |
| RB-05 | Deploy new image to staging | Auto via `image-build.yml` → `app-deploy.yml` chain |
| RB-06 | Deploy new image to prod | Manual `app-deploy.yml env=prod tag=v0.4.0 confirm=DEPLOY-PROD-v0.4.0` + GH env approval |
| RB-07 | Rollback prod | `app-deploy.yml tag=<previous-semver>` |
| RB-08 | Restore prod DB from backup (Phase 2) | Edit Cluster CR with `bootstrap.recovery.source`, reapply |
| RB-09 | Rotate KV secret | `terraform-prod.yml` triggers rotation; rolling restart consumer Deployments |
| RB-10 | Add a new env var to the app | Update `values-<env>.yaml`; re-run `app-deploy.yml` |
| RB-11 | Rotate Azure AD federated credential subject | Update Terraform `subject`, apply via `terraform-shared.yml`; wait ~5 min |
| RB-12 | Recover from spot eviction | Automatic via CAS; manual fallback: `aks-scale.yml usrpool count=2` |
| RB-13 | Tear down an entire environment | `terraform-<env>.yml action=destroy` (separate workflow file) + GH env approval |
| RB-14 | Cost overrun investigation | `az consumption usage list -g rg-dsv-<env>-eus2`; review top spenders |
| RB-15 | Force cert renewal | `kubectl annotate certificate dsv-app-tls cert-manager.io/issue-temporary-certificate-` |
| RB-16 | Migrate to Phase 2 DR cluster | (Phase 2 runbook — new workflow `aks-promote-dr.yml`) |

## Observability baseline (Phase 1)

- **Logs:** Container Insights from both clusters → `log-dsv-shared-eus2`,
  retention 30 days. Includes pod stdout/stderr, AKS control plane logs,
  Azure activity logs.
- **Metrics:** AKS node + pod metrics → Azure Monitor (free with Container
  Insights). Public IP availability test, 1 location, 5-min interval
  (~$0.50/mo, disabled when cluster intentionally stopped).
- **Alerts (Azure Monitor → email):**
  - Budget at 80% of $50/mo (cost guardrail)
  - AKS cluster running > 12h continuous (cost guardrail)
  - Postgres pod restarted > 3 times in 1h (KQL alert)
  - `db-backup-verify.yml` workflow failed (auto-opens GH issue)
  - Cert age > 60 days remaining (KQL from cert-renewal-heartbeat output)
- **Not in Phase 1** (Phase 2 enhancements): Prometheus / Loki / monitoring
  Grafana stack in `dsv-monitoring` namespace, distributed tracing,
  synthetic E2E tests.

## Final cost summary

### Phase 1 monthly cost at stated usage (prod 5%, staging 30%)

| Bucket | Monthly cost |
|---|---|
| Shared infrastructure | $8.20 |
| Prod always-on | $8.15 |
| Prod running (5% / ~36h) | $1.93 |
| Staging always-on | $5.90 |
| Staging running (30% / ~216h) | $11.57 |
| **Total** | **~$35.75/mo** |

Annual: ~$430. Plus domain renewal (~$12/yr) = ~$442/yr.

### Sensitivity analysis

| Scenario | Δ cost |
|---|---|
| Prod 24/7 | +$28/mo |
| Both clusters 24/7 | +$56/mo (exceeds budget) |
| No demos / no dev in a month | -$13.50/mo |
| Add Phase 2 DR cluster | +$10-15/mo |
| Add private API + Bastion | +$15/mo |
| Add App Gateway WAF | +$30/mo |
| Add full Prometheus stack | +$5-10/mo |

## Roadmap

### Phase 2 enhancements (medium-term)

1. Azure Static Web App landing page with "start the demo" button.
2. DR cluster in West US 2 (`aks-dsv-prod-wus2`).
3. Multi-AZ within prod region (`syspool min = 2`).
4. Private AKS API endpoint + Azure Bastion.
5. Pod Security Standards `Restricted` profile.
6. Image vulnerability scanning (Trivy + ACR Defender).
7. Platform monitoring stack in `dsv-monitoring` namespace (Prometheus, Loki, Promtail, Grafana).
8. PgBouncer connection pooling via CNPG `Pooler` CR.
9. HPA on Flask + synthetic load test (k6).
10. PR preview environments.
11. NetworkPolicy hardening via Cilium L7 policies.
12. KV secret rotation automation.

### Phase 3 enhancements (long-term)

1. Argo CD GitOps with image automation.
2. Argo Rollouts canary deploys.
3. Multi-region active-active.
4. Azure Front Door + WAF.
5. Postgres read replicas for analytics offload.
6. Cilium ClusterMesh between prod + DR.
7. SLO definitions + SLI dashboards.
8. OpenTelemetry distributed tracing.
9. Annual pen testing.
10. CIS Kubernetes Benchmark compliance.

## Implementation order (Phase 1 phasing)

1. **Foundation** (`infra/terraform/azure-shared/`): RGs, ACR, DNS zone, Log Analytics, Terraform state storage, GHA MIs, federated credentials.
2. **GitHub setup**: Flip repo to public, audit history, create environments, add repo variables.
3. **First image build**: Run `image-build.yml` from main to populate ACR.
4. **Staging infrastructure** (`infra/terraform/azure-staging/`): VNet, AKS cluster, Public IP, Key Vault, WAL storage, workload identities.
5. **Staging bring-up + bootstrap**: First `aks-up.yml`. Validates identity chain end-to-end.
6. **Staging app deploy**: First end-to-end deploy + smoke test.
7. **Iterate on staging**: Fix subtle issues without prod risk.
8. **Prod infrastructure**: Parallel to staging, lessons applied.
9. **Prod bring-up + bootstrap**.
10. **Prod app deploy**: Tagged release `v0.4.0-azure`.
11. **DNS cut-over**: Namecheap NS to Azure DNS; A records via Terraform.
12. **Observability hookup**: Container Insights, availability test, scheduled verification workflows.
13. **Stop both clusters**: Validate `aks-down.yml`; confirm stopped-state cost matches projection.
14. **Documentation pass**: Update `docs/how-to/` with AKS-specific install + redeploy guides.

## Open questions / deferred decisions

1. **Phase 2 DR trigger:** After 3 months of Phase 1 stability without issues.
2. **Phase 2 monitoring trigger:** When ~$10 of monthly headroom available.
3. **Cost ceiling escalation:** Documented in Phase 3 — only if real traffic warrants prod 24/7.
4. **Static landing page hosting:** Azure Static Web Apps (preferred, keeps all-Azure story) vs Cloudflare Pages.
5. **Repo visibility long-term:** Phase 1 = public (for free Environments + free Actions). If sensitive data ever lands, re-evaluate.

## References

- AKS Workload Identity overview: https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview
- CloudNativePG documentation: https://cloudnative-pg.io/documentation/current/
- GitHub OIDC for Azure: https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect
- cert-manager DNS-01 azuredns solver: https://cert-manager.io/docs/configuration/acme/dns01/azuredns/
- Azure CAF naming abbreviations: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations
- Existing prior design: `docs/superpowers/specs/2026-05-01-homelab-k8s-design.md`
