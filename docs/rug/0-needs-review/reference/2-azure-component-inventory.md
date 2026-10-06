# Azure component inventory — DineSafeViz

> [!NOTE]
> **Target state (v0.4.0, in progress).** This document describes the planned
> Azure/AKS architecture, not the currently deployed Proxmox environment. For
> the live deployment, see the [Proxmox install guide](../how-to/1-install/README.md).

Reference for architecture discussions. Covers region independence, subscription
model diagrams, and the full component list for a single prod deployment.

---

## Region independence

A "global" service is not tied to a single Azure region, so no single
region's health affects availability or DNS resolution. Azure deploys a
"regional" service to a specific region, and that service fails with that
region.

| Service | Classification | Notes |
|---|---|---|
| Azure DNS public zone | **Global** | Zone resource lives in a RG (has a location for billing purposes), but DNS queries are served from Azure's globally distributed DNS infrastructure. The RG's region has no effect on resolution. |
| Azure Container Registry (ACR) | **Regional storage, global endpoint** | Images are stored in the home region. The endpoint `<name>.azurecr.io` is accessible from anywhere. If the home region is down, pushes and pulls fail. Geo-replication (Premium tier only) adds redundancy. Basic tier: one region, no failover. |
| User-Assigned Managed Identity | **Regional resource, global identity** | The MI resource is placed in a region, but the underlying service principal lives in Entra ID (global). An MI created in East US 2 can authenticate from a workload running in West Europe. |
| Azure Key Vault | **Regional** | Secrets are replicated within the region's paired datacenter, but the vault is a regional resource. A vault in East US 2 is unavailable if East US 2 is down. |
| AKS cluster | **Regional** | Control plane and node pools run in a specific region. Availability Zones spread nodes across datacenters *within* the region — they do not protect against full-region failure. |
| VNet / Subnet / NSG | **Regional** | Must be co-located with resources that attach to them. A VNet in East US 2 cannot contain subnets in West US 2. |
| Public IP address | **Regional** | Standard SKU supports Availability Zones within a region. Cannot be moved between regions. |
| Azure Blob Storage | **Regional** | LRS: three copies in one datacenter. ZRS: three AZs in one region. GRS: replicates asynchronously to a paired region. |
| Log Analytics Workspace | **Regional** | Log data is stored in the specified region. |
| Azure Load Balancer (auto) | **Regional** | Created automatically by AKS when a Kubernetes `Service` of type `LoadBalancer` is created. |
| Managed Disks (PVCs) | **Regional** | Provisioned in the same zone as the pod that mounts them. |

**Practical implication for this project:** Everything except DNS is regional.
If East US 2 has an outage, the whole deployment is down. Phase 2 disaster
recovery (DR), with a West US 2 cluster, addresses this. For Phase 1, the
choice of region is cosmetic, so pick the one with the right services at the
right price.

---

## Diagram A — Current design: single subscription, three resource groups

```
┌─────────────────────────── Azure Subscription: DineSafeViz ───────────────────────────┐
│                                                                                         │
│  ┌──────────────── rg-dsv-shared-eus2 ─────────────────┐                              │
│  │  ACR  (acrdsv<rnd>.azurecr.io)   [global endpoint]   │                              │
│  │  DNS Zone  (dinesafeviz.com)      [globally served]   │                              │
│  │  Log Analytics Workspace                              │                              │
│  │  Storage Account  (TF state blobs)                    │                              │
│  │  MI: id-gha-dsv-shared-eus2  ──┐                     │                              │
│  │  MI: id-gha-dsv-prod-eus2    ──┼── federated OIDC    │                              │
│  │  MI: id-gha-dsv-stg-eus2    ──┘    → GitHub Actions  │                              │
│  └──────────────────────────────────────────────────────┘                              │
│           │ AcrPull / AcrPush                │ DNS Zone Contributor                    │
│           ▼                                  ▼                                         │
│  ┌──── rg-dsv-prod-eus2 ────────────────────────────────────────┐                     │
│  │  VNet 10.50.0.0/16                                            │                     │
│  │    ├─ snet-aksnodes-prod  10.50.0.0/22                        │                     │
│  │    ├─ snet-akspods-prod   10.50.4.0/22  (CNI Overlay)         │                     │
│  │    └─ snet-lb-prod        10.50.8.0/24  (reserved)            │                     │
│  │  NSG  (node subnet rules)                                     │                     │
│  │  Public IP  pip-dsv-ingress-prod-eus2  (static, Standard)     │                     │
│  │  AKS  aks-dsv-prod-eus2                                       │                     │
│  │    ├─ system pool  1–2 nodes  Standard_D2s_v3  on-demand      │                     │
│  │    └─ user pool    1–3 nodes  Standard_D2s_v3  spot           │                     │
│  │  Key Vault  kv-dsv-prod-<rnd>                                 │                     │
│  │  Storage Account  stdsvwalprodeus2<rnd>  (GRS, WAL/backup)    │                     │
│  │  MI: id-aks-controlplane-prod-eus2  (AKS control plane)       │                     │
│  │  MI: id-aks-cnpg-prod-eus2          (CNPG WAL — Workload ID)  │                     │
│  │  MI: id-aks-certmgr-prod-eus2       (cert-manager — WI)       │                     │
│  │  MI: id-aks-kvcsi-prod-eus2         (CSI Secrets Store — WI)  │                     │
│  └───────────────────────────────────────────────────────────────┘                     │
│                                                                                         │
│  ┌──── rg-dsv-stg-eus2 ─────────────────────────────────────────┐                     │
│  │  (parallel structure to prod — smaller PVCs, LRS WAL storage) │                     │
│  │  VNet 10.51.0.0/16                                            │                     │
│  │  AKS  aks-dsv-stg-eus2                                        │                     │
│  │  Key Vault  kv-dsv-stg-<rnd>                                  │                     │
│  │  Storage Account  (WAL, LRS)                                  │                     │
│  │  MI: id-aks-controlplane-stg-eus2                             │                     │
│  │  MI: id-aks-cnpg-stg-eus2                                     │                     │
│  │  MI: id-aks-certmgr-stg-eus2                                  │                     │
│  │  MI: id-aks-kvcsi-stg-eus2                                    │                     │
│  └───────────────────────────────────────────────────────────────┘                     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

Cross-cutting wires (all within one subscription — no extra auth required):
  id-aks-controlplane-prod  → AcrPull on ACR
  id-aks-certmgr-prod       → DNS Zone Contributor on DNS Zone
  id-aks-cnpg-prod          → Storage Blob Data Contributor on WAL storage account
  id-aks-kvcsi-prod         → Key Vault Secrets User on kv-dsv-prod-<rnd>
  id-gha-dsv-prod           → AKS Contributor on rg-dsv-prod-eus2, AcrPush on ACR
  (stg equivalents are identical, scoped to stg resources)
```

---

## Diagram B — Three-subscription model

```
┌────── Azure Subscription: DineSafeViz-Shared ──────────────────────┐
│  rg-dsv-shared-eus2                                                  │
│    ACR  (acrdsv<rnd>.azurecr.io)                                     │
│    DNS Zone  (dinesafeviz.com)                                       │
│    Log Analytics Workspace                                           │
│    Storage Account  (TF state for ALL three root modules)            │
│    MI: id-gha-dsv-shared-eus2  ─── OIDC → GitHub Actions            │
│    MI: id-gha-dsv-prod-eus2    ─── OIDC → GitHub Actions (prod)     │
│    MI: id-gha-dsv-stg-eus2     ─── OIDC → GitHub Actions (stg)      │
└──────────────────────────────────────────────────────────────────────┘
         │                                    │
         │ cross-subscription RBAC            │ cross-subscription RBAC
         │ (AcrPull, DNS Zone Contributor,    │ (same — scoped to stg MIs)
         │  Log Analytics Contributor)        │
         ▼                                    ▼
┌── Subscription: DineSafeViz-Prod ──┐  ┌── Subscription: DineSafeViz-NonProd ──┐
│  rg-dsv-prod-eus2                   │  │  rg-dsv-stg-eus2                       │
│    VNet / Subnets / NSG             │  │    VNet / Subnets / NSG                │
│    AKS  aks-dsv-prod-eus2           │  │    AKS  aks-dsv-stg-eus2               │
│    Public IP                        │  │    Public IP                           │
│    Key Vault  kv-dsv-prod-<rnd>     │  │    Key Vault  kv-dsv-stg-<rnd>         │
│    Storage Account  (WAL, GRS)      │  │    Storage Account  (WAL, LRS)         │
│    MI: id-aks-controlplane-prod     │  │    MI: id-aks-controlplane-stg         │
│    MI: id-aks-cnpg-prod             │  │    MI: id-aks-cnpg-stg                 │
│    MI: id-aks-certmgr-prod          │  │    MI: id-aks-certmgr-stg              │
│    MI: id-aks-kvcsi-prod            │  │    MI: id-aks-kvcsi-stg                │
└─────────────────────────────────────┘  └────────────────────────────────────────┘

Complexity added vs. single subscription:
  ✗ Every cross-subscription RBAC grant needs the target resource's full
    resource ID (includes subscription GUID as a literal string in Terraform)
  ✗ Terraform needs provider aliases: one azurerm provider block per subscription
    targeted in a root module. azure-prod needs providers for BOTH prod and shared
    subscriptions so it can read ACR/DNS resource IDs and write role assignments.
  ✗ The TF state storage account lives in DineSafeViz-Shared, but
    azure-prod.tfstate describes resources in DineSafeViz-Prod. The backend
    config for azure-prod points at a storage account in a different subscription.
  ✗ GitHub Actions workflows need PROD_SUBSCRIPTION_ID and SHARED_SUBSCRIPTION_ID
    as separate variables. azure/login@v2 targets prod sub; terraform then needs
    shared sub ID passed as a variable for cross-subscription data sources.
  ✗ CLI operations require --subscription flags or repeated `az account set` calls.
```

---

## Component inventory — single prod deployment

One subscription, two resource groups. No staging.

### Tier 0 — bootstrapped manually before Terraform runs

These must exist before `terraform init` can use them as a backend.

| Component | Type | Notes |
|---|---|---|
| `rg-dsv-shared-eus2` | Resource Group | Created via `az group create` |
| `stdsvtfsteus2<rnd>` | Storage Account (Standard LRS) | TF state backend |
| `tfstate` container | Blob container inside above | Holds `.tfstate` blobs |

### Tier 1 — provisioned by `azure-shared` Terraform root module

These are cross-cutting resources not tied to a specific cluster.

| Component | Azure Type | Resource Name | Notes |
|---|---|---|---|
| Shared resource group | `azurerm_resource_group` | `rg-dsv-shared-eus2` | Already created in Tier 0; imported or data-sourced |
| Container registry | `azurerm_container_registry` | `acrdsv<rnd>` | Basic SKU; geo-redundancy not available at Basic |
| DNS zone | `azurerm_dns_zone` | `dinesafeviz.com` | Public zone; NS records copied to Namecheap at cutover |
| Log Analytics workspace | `azurerm_log_analytics_workspace` | `log-dsv-shared-eus2` | 30-day retention (free tier threshold) |
| TF state storage | `azurerm_storage_account` | `stdsvtfsteus2<rnd>` | Already bootstrapped; Terraform manages lifecycle tags |
| GHA shared MI | `azurerm_user_assigned_identity` | `id-gha-dsv-shared-eus2` | Used by image-build and shared infra workflows |
| GHA prod MI | `azurerm_user_assigned_identity` | `id-gha-dsv-prod-eus2` | Used by terraform-prod.yml and app-deploy workflows |
| Federated credential — shared env | `azurerm_federated_identity_credential` | — | Subject: `repo:im-kenough/DineSafeViz:environment:dsv-shared` |
| Federated credential — prod env | `azurerm_federated_identity_credential` | — | Subject: `repo:im-kenough/DineSafeViz:environment:prod` |
| Federated credential — prod tags | `azurerm_federated_identity_credential` | — | Subject: `repo:im-kenough/DineSafeViz:ref:refs/tags/v*` |
| Role: GHA shared → ACR push | `azurerm_role_assignment` | — | `AcrPush` on `acrdsv<rnd>` |
| Role: GHA shared → shared RG | `azurerm_role_assignment` | — | `Contributor` on `rg-dsv-shared-eus2` |
| Role: GHA shared → TF state | `azurerm_role_assignment` | — | `Storage Blob Data Contributor` on TF state account |
| Role: GHA shared → DNS | `azurerm_role_assignment` | — | `DNS Zone Contributor` on `dinesafeviz.com` |
| Role: GHA prod → AKS | `azurerm_role_assignment` | — | `Azure Kubernetes Service Contributor` on `rg-dsv-prod-eus2` |
| Role: GHA prod → ACR push | `azurerm_role_assignment` | — | `AcrPush` on `acrdsv<rnd>` |

### Tier 2 — provisioned by `azure-prod` Terraform root module

These are the cluster-level resources.

| Component | Azure Type | Resource Name | Notes |
|---|---|---|---|
| Prod resource group | `azurerm_resource_group` | `rg-dsv-prod-eus2` | — |
| VNet | `azurerm_virtual_network` | `vnet-dsv-prod-eus2` | `10.50.0.0/16` |
| Node subnet | `azurerm_subnet` | `snet-dsv-aksnodes-prod-eus2` | `10.50.0.0/22` — node VMs attach here |
| Pod subnet | `azurerm_subnet` | `snet-dsv-akspods-prod-eus2` | `10.50.4.0/22` — Azure CNI Overlay pod IPs |
| LB subnet | `azurerm_subnet` | `snet-dsv-lb-prod-eus2` | `10.50.8.0/24` — reserved for internal LB if ever added |
| NSG | `azurerm_network_security_group` | `nsg-dsv-aksnodes-prod-eus2` | Default-deny + AKS-required inbound rules |
| NSG association | `azurerm_subnet_network_security_group_association` | — | Binds NSG to node subnet |
| Public IP | `azurerm_public_ip` | `pip-dsv-ingress-prod-eus2` | Static, Standard SKU; annotated onto NGINX ingress |
| AKS cluster | `azurerm_kubernetes_cluster` | `aks-dsv-prod-eus2` | Workload Identity + OIDC issuer enabled; Cilium network policy |
| System node pool | (inside AKS resource) | `system` | 1–2 nodes, Standard_D2s_v3, on-demand, AZ spread |
| Spot user node pool | `azurerm_kubernetes_cluster_node_pool` | `user` | 1–3 nodes, Standard_D2s_v3, spot, AZ spread |
| Key Vault | `azurerm_key_vault` | `kv-dsv-prod-<rnd>` | RBAC auth model; soft-delete + purge protection on |
| WAL storage account | `azurerm_storage_account` | `stdsvwalprodeus2<rnd>` | Standard LRS or GRS; holds CNPG WAL + basebackups |
| WAL blob container | `azurerm_storage_container` | `cnpg-wal-prod` | — |
| Backup blob container | `azurerm_storage_container` | `cnpg-basebackups-prod` | — |
| Control plane MI | `azurerm_user_assigned_identity` | `id-aks-controlplane-prod-eus2` | Assigned to AKS cluster itself |
| CNPG MI | `azurerm_user_assigned_identity` | `id-aks-cnpg-prod-eus2` | Workload Identity for CNPG pods |
| cert-manager MI | `azurerm_user_assigned_identity` | `id-aks-certmgr-prod-eus2` | Workload Identity for cert-manager DNS-01 solver |
| CSI Secrets Store MI | `azurerm_user_assigned_identity` | `id-aks-kvcsi-prod-eus2` | Workload Identity for Key Vault CSI driver |
| Role: control plane → ACR | `azurerm_role_assignment` | — | `AcrPull` on `acrdsv<rnd>` |
| Role: control plane → VNet | `azurerm_role_assignment` | — | `Network Contributor` on `vnet-dsv-prod-eus2` |
| Role: CNPG → WAL storage | `azurerm_role_assignment` | — | `Storage Blob Data Contributor` on `stdsvwalprodeus2<rnd>` |
| Role: cert-manager → DNS | `azurerm_role_assignment` | — | `DNS Zone Contributor` on `dinesafeviz.com` |
| Role: CSI driver → KV | `azurerm_role_assignment` | — | `Key Vault Secrets User` on `kv-dsv-prod-<rnd>` |
| KV secret — analytics admin | `azurerm_key_vault_secret` | `analytics-admin-password` | Grafana/analytics admin credential |
| Federated credential — CNPG | `azurerm_federated_identity_credential` | — | Links CNPG K8s ServiceAccount → `id-aks-cnpg-prod-eus2` |
| Federated credential — cert-manager | `azurerm_federated_identity_credential` | — | Links cert-manager K8s SA → `id-aks-certmgr-prod-eus2` |
| Federated credential — CSI driver | `azurerm_federated_identity_credential` | — | Links CSI K8s SA → `id-aks-kvcsi-prod-eus2` |
| Diagnostic settings | `azurerm_monitor_diagnostic_setting` | — | AKS control plane logs → Log Analytics workspace |

### Tier 3 — auto-provisioned by AKS (the node resource group)

AKS creates a second resource group (`MC_rg-dsv-prod-eus2_aks-dsv-prod-eus2_eastus2`) and manages everything inside it. **You do not write Terraform for these.** Runbooks may need to reference them.

| Component | Notes |
|---|---|
| VMSS — system pool | The actual VMs backing the system node pool |
| VMSS — user pool | The actual VMs backing the spot user node pool |
| VM instances | Individual nodes; scale up/down automatically |
| Managed Disks | One OS disk per node; data disks created as PVCs are bound |
| Route table | Azure CNI Overlay adds pod routes here |
| Network interfaces (NICs) | One NIC per node, attached to `snet-dsv-aksnodes-prod-eus2` |
| Azure Load Balancer | Created when NGINX ingress Service of type `LoadBalancer` is applied |

Microsoft **fully manages** the AKS control plane itself (the API server, etcd, scheduler), and it does not appear in your subscription at all. You don't pay a separate charge for it. The AKS cluster resource (`aks-dsv-prod-eus2`) has no hourly control plane charge.

### Tier 4 — provisioned by Helm / Helmfile (inside the cluster)

These are Kubernetes-layer resources, not Azure resources. They run as pods inside the cluster. Some of them trigger Azure API calls that create Tier 3 resources.

| Component | What it does | Azure side-effect |
|---|---|---|
| NGINX Ingress Controller | Proxies external HTTP/S traffic to pods | Creates Azure Load Balancer (Tier 3) |
| cert-manager | Manages TLS certificates via Let's Encrypt DNS-01 | Writes DNS TXT records to Azure DNS zone |
| CSI Secrets Store + Azure provider | Mounts Key Vault secrets as pod volumes | Reads secrets from Key Vault |
| CloudNativePG operator | Manages the PostgreSQL cluster | Writes WAL files and basebackups to Azure Blob |
| PostgreSQL cluster (CNPG) | The database itself | Provisions Managed Disks as PVCs |
| DineSafeViz app (dsv-app) | Flask web app | — |
| DineSafeViz analytics (dsv-analytics) | Grafana instance | — |

---

## Total resource count — single prod deployment

| Tier | Count | Provisioner |
|---|---|---|
| 0 — bootstrap | 3 | Manual (az CLI) |
| 1 — shared | ~16 | Terraform `azure-shared` |
| 2 — prod cluster | ~28 | Terraform `azure-prod` |
| 3 — node RG | ~6–10 (varies with node count) | AKS-managed |
| 4 — Kubernetes | ~7 workloads | Helmfile |

Rough total of Terraform-managed resources: **~44**, not counting role assignments
on objects that don't exist yet at plan time (Terraform creates federated
credentials after the AKS cluster comes up and it knows the OIDC issuer URL).
