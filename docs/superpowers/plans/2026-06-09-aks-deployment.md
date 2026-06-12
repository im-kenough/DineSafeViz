# DineSafeViz on Azure AKS — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up two AKS clusters (prod + staging) in East US 2 with a stop-by-default lifecycle, deploy DineSafeViz via Helm + CloudNativePG, and wire GitHub Actions OIDC + Workload Identity end-to-end — all inside a ~USD $36/mo steady-state budget.

**Architecture:** Separate AKS clusters in dedicated resource groups, one shared resource group for cross-cutting infrastructure (ACR, DNS, Log Analytics, GHA managed identities + federated credentials). Terraform-managed Azure resources; Helm + Helmfile-managed Kubernetes workloads. All Kubernetes secrets either CNPG-owned (Postgres credentials), cert-manager-owned (TLS), or Azure Key Vault-projected (analytics admin). No long-lived credentials anywhere: AKS uses managed-identity-based ACR pulls; GitHub Actions uses OIDC federated identity. Cluster autoscaler configured but minimums kept at 1 to match stop-by-default lifecycle.

**Tech Stack:** Terraform (Azure provider 4.x), Helm 3.x, Helmfile 0.x, GitHub Actions, Azure AKS, Azure Container Registry, Azure Key Vault, Azure DNS, Azure Blob Storage (GRS), CloudNativePG 1.24.x, ingress-nginx 4.x, cert-manager 1.16.x, csi-secrets-store-provider-azure 1.5.x

**Spec:** `docs/superpowers/specs/2026-06-09-aks-deployment-design.md`

**Milestone:** v0.4.0

---

## File Structure

All new files live under `infra/` (additions to existing tree) and `.github/workflows/` (new workflows). No application source code in `src/dsv-*` changes.

```
infra/
├── terraform/
│   ├── azure-shared/              # Epic 2
│   │   ├── backend.tf             # Azure Storage state backend
│   │   ├── main.tf                # provider, common locals
│   │   ├── resource_groups.tf
│   │   ├── acr.tf
│   │   ├── dns_zone.tf
│   │   ├── log_analytics.tf
│   │   ├── managed_identities_gha.tf  # GHA OIDC MIs + federated creds
│   │   ├── role_assignments_gha.tf
│   │   ├── tfstate_storage.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars.example
│   ├── azure-staging/             # Epic 4
│   │   ├── backend.tf
│   │   ├── main.tf
│   │   ├── network.tf             # VNet, subnets, NSG, Public IP
│   │   ├── aks.tf
│   │   ├── key_vault.tf
│   │   ├── storage_wal.tf
│   │   ├── managed_identities.tf  # control plane + workload MIs
│   │   ├── role_assignments.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars.example
│   ├── azure-prod/                # Epic 9 — structural copy of azure-staging
│   │   └── (parallel files)
│   └── proxmox/                   # existing, untouched
├── helm/
│   ├── cluster-bootstrap/         # Epic 5
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-prod.yaml
│   │   ├── values-staging.yaml
│   │   └── templates/
│   │       ├── _helpers.tpl
│   │       ├── namespaces.yaml
│   │       ├── storageclass-standard-ssd.yaml
│   │       └── clusterissuer-letsencrypt.yaml
│   └── dinesafeviz/               # Epic 6
│       ├── Chart.yaml
│       ├── Chart.lock
│       ├── values.yaml
│       ├── values-prod.yaml
│       ├── values-staging.yaml
│       └── templates/
│           ├── _helpers.tpl
│           ├── serviceaccount-app.yaml
│           ├── serviceaccount-analytics.yaml
│           ├── postgres-cluster.yaml
│           ├── postgres-scheduledbackup.yaml
│           ├── postgres-init-configmap.yaml
│           ├── secretproviderclass.yaml
│           ├── app-deployment.yaml
│           ├── app-service.yaml
│           ├── app-ingress.yaml
│           ├── app-certificate.yaml
│           ├── analytics-pvc.yaml
│           ├── analytics-deployment.yaml
│           ├── analytics-service.yaml
│           ├── analytics-ingress.yaml
│           ├── analytics-configmap-datasource.yaml
│           ├── analytics-configmap-dashboards.yaml
│           ├── networkpolicy-default-deny.yaml
│           ├── networkpolicy-allow-ingress-to-app.yaml
│           ├── networkpolicy-allow-app-to-postgres.yaml
│           ├── networkpolicy-allow-analytics-to-postgres.yaml
│           ├── networkpolicy-allow-egress-kube-dns.yaml
│           ├── networkpolicy-allow-egress-azure-blob.yaml
│           ├── networkpolicy-allow-egress-azuredns.yaml
│           ├── networkpolicy-allow-egress-acme.yaml
│           ├── init-db-job.yaml
│           ├── init-analytics-job.yaml
│           └── tests/
│               └── connection-test.yaml
├── helmfile.yaml                  # Epic 5/6
└── docs/                          # Epic 13 — refresh
    └── how-to/
        ├── 7-aks-setup.md         # NEW
        └── 8-aks-operations.md    # NEW

.github/workflows/
├── _azure-auth.yml                # Epic 3 — reusable composite
├── image-build.yml                # Epic 3
├── terraform-shared.yml           # Epic 2
├── terraform-staging.yml          # Epic 4
├── terraform-prod.yml             # Epic 9
├── aks-up.yml                     # Epic 7
├── aks-down.yml                   # Epic 7
├── aks-scale.yml                  # Epic 7
├── app-deploy.yml                 # Epic 7
├── cert-renewal-heartbeat.yml     # Epic 12
├── acr-cleanup.yml                # Epic 12
└── db-backup-verify.yml           # Epic 12
```

---

## Epic 1 — Public repo + GitHub Environments setup

**Goal:** Flip the repo to public, audit for committed secrets, create `prod` and `staging` GitHub Environments, populate Actions variables.

**Why first:** OIDC federated credentials with environment-scoped subjects require Environments to exist. Public repo also unlocks free Actions minutes.

**Files:** No repo file changes. All GitHub-side configuration.

- [ ] **Step 1: Audit git history for secrets**

```bash
cd /home/sam/SCM/github/DineSafeViz
git log -p --all | grep -iE '(password|secret|token|api[_-]?key)\s*[=:]' | head -50
# Review any hits. If real secrets ever landed:
#   - Decide on git filter-repo to scrub, or rotate the leaked secrets and accept history.
# Expected for this repo: only hits are in test fixtures, docs, or Ansible Vault references.
```

- [ ] **Step 2: Change repo visibility to public**

```bash
gh repo edit im-kenough/DineSafeViz --visibility public --accept-visibility-change-consequences
gh repo view im-kenough/DineSafeViz --json visibility -q .visibility
# Expected: "PUBLIC"
```

- [ ] **Step 3: Create `prod` environment with reviewer protection**

```bash
gh api -X PUT repos/im-kenough/DineSafeViz/environments/prod \
  -f 'reviewers[][type]=User' \
  -F 'reviewers[][id]=$(gh api users/im-kenough -q .id)' \
  -f 'deployment_branch_policy[protected_branches]=false' \
  -f 'deployment_branch_policy[custom_branch_policies]=true'

# Then add deployment branch policies for main and v* tags:
gh api -X POST repos/im-kenough/DineSafeViz/environments/prod/deployment-branch-policies \
  -f name=main
gh api -X POST repos/im-kenough/DineSafeViz/environments/prod/deployment-branch-policies \
  -f name='v*' -f type=tag
```

- [ ] **Step 4: Create `staging` environment (no reviewer)**

```bash
gh api -X PUT repos/im-kenough/DineSafeViz/environments/staging
# Default: no reviewers, all branches allowed.
```

- [ ] **Step 5: Verify environments**

```bash
gh api repos/im-kenough/DineSafeViz/environments --jq '.environments[].name'
# Expected: prod, staging
```

- [ ] **Step 6: Provision Azure subscription**

Create Microsoft account if needed → sign up at https://azure.microsoft.com/free → confirm Pay-As-You-Go billing → record:
- Tenant ID (Azure Portal → Azure Active Directory → Properties → Tenant ID)
- Subscription ID (Azure Portal → Subscriptions → click subscription → Subscription ID)

- [ ] **Step 7: Add GitHub repo variables (will be populated with values from Epic 2 outputs)**

```bash
gh variable set AZURE_TENANT_ID --body "<tenant-guid>"
gh variable set AZURE_SUBSCRIPTION_ID --body "<subscription-guid>"
# AZURE_CLIENT_ID_PROD, AZURE_CLIENT_ID_STAGING, AZURE_CLIENT_ID_SHARED added in Epic 2 Step 12.
```

- [ ] **Step 8: Commit a no-op marker for the public flip**

Update `README.md` to mention this repo is now publicly browsable for portfolio purposes.

```bash
git checkout -b feat/aks-phase-1
# Edit README.md (small note in intro paragraph)
git add README.md
git commit -m "docs: note repo is public for portfolio browsing"
```

---

## Epic 2 — Shared Azure infrastructure (Terraform)

**Goal:** Provision the cross-cutting Azure resources via Terraform: shared resource group, ACR, DNS zone, Log Analytics workspace, Terraform state storage, all GitHub Actions managed identities, and their federated identity credentials.

**Why second:** Foundation for everything that follows. GHA workflows in Epic 3 onward need the managed identities to exist.

**Prereq:** Epic 1 complete (Azure subscription provisioned).

**Files:**
- Create: `infra/terraform/azure-shared/{backend.tf,main.tf,resource_groups.tf,acr.tf,dns_zone.tf,log_analytics.tf,managed_identities_gha.tf,role_assignments_gha.tf,tfstate_storage.tf,variables.tf,outputs.tf,terraform.tfvars.example}`

- [ ] **Step 1: Manually bootstrap the Terraform state storage account**

The state storage account must exist before Terraform can use it as a backend. Bootstrap manually via Azure CLI:

```bash
az login
az account set --subscription "<subscription-guid>"

# Create bootstrap RG and storage account
az group create --name rg-dsv-shared-eus2 --location eastus2
RND=$(openssl rand -hex 2)
az storage account create \
  --name "stdsvtfsteus2${RND}" \
  --resource-group rg-dsv-shared-eus2 \
  --location eastus2 \
  --sku Standard_GRS \
  --kind StorageV2 \
  --allow-blob-public-access false \
  --min-tls-version TLS1_2
az storage container create \
  --account-name "stdsvtfsteus2${RND}" \
  --name tfstate \
  --auth-mode login
echo "Record this random suffix for backend config: ${RND}"
```

- [ ] **Step 2: Write `backend.tf`**

```bash
mkdir -p /home/sam/SCM/github/DineSafeViz/infra/terraform/azure-shared
```

Create `infra/terraform/azure-shared/backend.tf`:

```hcl
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-dsv-shared-eus2"
    storage_account_name = "stdsvtfsteus2<RND>"  # replace with actual random suffix
    container_name       = "tfstate"
    key                  = "azure-shared.tfstate"
    use_azuread_auth     = true
  }
}
```

- [ ] **Step 3: Write `main.tf` (provider + locals)**

Create `infra/terraform/azure-shared/main.tf`:

```hcl
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

provider "azuread" {}

data "azurerm_client_config" "current" {}

locals {
  workload = "dsv"
  region   = "eus2"
  tags = {
    workload    = "dinesafeviz"
    environment = "shared"
    managed_by  = "terraform"
    cost_center = "personal"
    owner       = "im-kenough"
    repo        = "github.com/im-kenough/DineSafeViz"
  }
}

resource "random_string" "suffix" {
  length  = 4
  upper   = false
  special = false
}
```

- [ ] **Step 4: Write `resource_groups.tf`**

```hcl
resource "azurerm_resource_group" "shared" {
  name     = "rg-${local.workload}-shared-${local.region}"
  location = "eastus2"
  tags     = local.tags
}
```

- [ ] **Step 5: Write `acr.tf`**

```hcl
resource "azurerm_container_registry" "main" {
  name                = "acr${local.workload}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.shared.name
  location            = azurerm_resource_group.shared.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}
```

- [ ] **Step 6: Write `dns_zone.tf`**

```hcl
resource "azurerm_dns_zone" "main" {
  name                = "dinesafeviz.com"
  resource_group_name = azurerm_resource_group.shared.name
  tags                = local.tags
}
```

- [ ] **Step 7: Write `log_analytics.tf`**

```hcl
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.workload}-shared-${local.region}"
  resource_group_name = azurerm_resource_group.shared.name
  location            = azurerm_resource_group.shared.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}
```

- [ ] **Step 8: Write `managed_identities_gha.tf`**

```hcl
resource "azurerm_user_assigned_identity" "gha_prod" {
  name                = "id-gha-${local.workload}-prod-${local.region}"
  resource_group_name = azurerm_resource_group.shared.name
  location            = azurerm_resource_group.shared.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "gha_staging" {
  name                = "id-gha-${local.workload}-stg-${local.region}"
  resource_group_name = azurerm_resource_group.shared.name
  location            = azurerm_resource_group.shared.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "gha_shared" {
  name                = "id-gha-${local.workload}-shared-${local.region}"
  resource_group_name = azurerm_resource_group.shared.name
  location            = azurerm_resource_group.shared.location
  tags                = local.tags
}

# Federated credentials — prod
resource "azurerm_federated_identity_credential" "gha_prod_env" {
  name                = "gha-prod-env"
  resource_group_name = azurerm_resource_group.shared.name
  parent_id           = azurerm_user_assigned_identity.gha_prod.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:im-kenough/DineSafeViz:environment:prod"
}

resource "azurerm_federated_identity_credential" "gha_prod_tag" {
  name                = "gha-prod-tag"
  resource_group_name = azurerm_resource_group.shared.name
  parent_id           = azurerm_user_assigned_identity.gha_prod.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:im-kenough/DineSafeViz:ref:refs/tags/v*"
}

# Federated credentials — staging
resource "azurerm_federated_identity_credential" "gha_stg_env" {
  name                = "gha-stg-env"
  resource_group_name = azurerm_resource_group.shared.name
  parent_id           = azurerm_user_assigned_identity.gha_staging.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:im-kenough/DineSafeViz:environment:staging"
}

resource "azurerm_federated_identity_credential" "gha_stg_pr" {
  name                = "gha-stg-pr"
  resource_group_name = azurerm_resource_group.shared.name
  parent_id           = azurerm_user_assigned_identity.gha_staging.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:im-kenough/DineSafeViz:pull_request"
}

# Federated credentials — shared
resource "azurerm_federated_identity_credential" "gha_shared_main" {
  name                = "gha-shared-main"
  resource_group_name = azurerm_resource_group.shared.name
  parent_id           = azurerm_user_assigned_identity.gha_shared.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:im-kenough/DineSafeViz:ref:refs/heads/main"
}

resource "azurerm_federated_identity_credential" "gha_shared_pr" {
  name                = "gha-shared-pr"
  resource_group_name = azurerm_resource_group.shared.name
  parent_id           = azurerm_user_assigned_identity.gha_shared.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:im-kenough/DineSafeViz:pull_request"
}

resource "azurerm_federated_identity_credential" "gha_shared_tag" {
  name                = "gha-shared-tag"
  resource_group_name = azurerm_resource_group.shared.name
  parent_id           = azurerm_user_assigned_identity.gha_shared.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:im-kenough/DineSafeViz:ref:refs/tags/v*"
}
```

- [ ] **Step 9: Write `role_assignments_gha.tf`**

```hcl
# Shared MI: AcrPush on ACR
resource "azurerm_role_assignment" "gha_shared_acrpush" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.gha_shared.principal_id
}

# Shared MI: DNS Zone Contributor on the zone
resource "azurerm_role_assignment" "gha_shared_dns" {
  scope                = azurerm_dns_zone.main.id
  role_definition_name = "DNS Zone Contributor"
  principal_id         = azurerm_user_assigned_identity.gha_shared.principal_id
}

# Shared MI: Contributor on shared RG (for Terraform apply on this layer)
resource "azurerm_role_assignment" "gha_shared_rg_contributor" {
  scope                = azurerm_resource_group.shared.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.gha_shared.principal_id
}

# (Prod and staging RG contributor assignments will be created in azure-prod/ and azure-staging/
# referencing these MIs by data source.)
```

- [ ] **Step 10: Write `variables.tf`**

```hcl
variable "github_repo" {
  type        = string
  default     = "im-kenough/DineSafeViz"
  description = "GitHub repo in owner/repo form. Drives federated credential subjects."
}
```

- [ ] **Step 11: Write `outputs.tf`**

```hcl
output "shared_resource_group_name" {
  value = azurerm_resource_group.shared.name
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "acr_id" {
  value = azurerm_container_registry.main.id
}

output "dns_zone_name" {
  value = azurerm_dns_zone.main.name
}

output "dns_zone_id" {
  value = azurerm_dns_zone.main.id
}

output "dns_zone_name_servers" {
  value       = azurerm_dns_zone.main.name_servers
  description = "Configure these 4 NS records at Namecheap to delegate the domain."
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.main.id
}

output "gha_prod_client_id" {
  value       = azurerm_user_assigned_identity.gha_prod.client_id
  description = "Set as GitHub repo variable AZURE_CLIENT_ID_PROD."
}

output "gha_staging_client_id" {
  value       = azurerm_user_assigned_identity.gha_staging.client_id
  description = "Set as GitHub repo variable AZURE_CLIENT_ID_STAGING."
}

output "gha_shared_client_id" {
  value       = azurerm_user_assigned_identity.gha_shared.client_id
  description = "Set as GitHub repo variable AZURE_CLIENT_ID_SHARED."
}
```

- [ ] **Step 12: Init, plan, apply locally**

```bash
cd infra/terraform/azure-shared
terraform init
terraform plan -out=tfplan
# Review: ~10-12 resources to create
terraform apply tfplan
# Expected: Apply complete! Resources: 12 added, 0 changed, 0 destroyed.
```

- [ ] **Step 13: Capture outputs into GitHub repo variables**

```bash
TENANT_ID=$(az account show --query tenantId -o tsv)
SUB_ID=$(az account show --query id -o tsv)
gh variable set AZURE_TENANT_ID --body "$TENANT_ID"
gh variable set AZURE_SUBSCRIPTION_ID --body "$SUB_ID"
gh variable set AZURE_CLIENT_ID_PROD --body "$(terraform output -raw gha_prod_client_id)"
gh variable set AZURE_CLIENT_ID_STAGING --body "$(terraform output -raw gha_staging_client_id)"
gh variable set AZURE_CLIENT_ID_SHARED --body "$(terraform output -raw gha_shared_client_id)"
gh variable set ACR_LOGIN_SERVER --body "$(terraform output -raw acr_login_server)"
```

- [ ] **Step 14: Configure Namecheap NS delegation**

Manually at Namecheap: Domain List → Manage → Nameservers → Custom DNS → paste the 4 hostnames from `terraform output dns_zone_name_servers`. Propagation 24-48h on first delegation.

- [ ] **Step 15: Commit Terraform module**

```bash
cd /home/sam/SCM/github/DineSafeViz
git add infra/terraform/azure-shared/
git commit -m "infra: bootstrap shared Azure resources via Terraform

- Resource group rg-dsv-shared-eus2
- ACR acrdsv<rnd> (Basic)
- DNS zone dinesafeviz.com
- Log Analytics workspace
- GitHub Actions managed identities + federated credentials (prod/staging/shared)
- Role assignments: shared MI gets AcrPush, DNS Zone Contributor, RG Contributor"
```

---

## Epic 3 — Image build CI/CD workflow

**Goal:** Stand up `image-build.yml` + reusable `_azure-auth.yml` composite so any code push produces `acrdsv<rnd>.azurecr.io/dinesafeviz/app:<tag>`.

**Prereq:** Epic 2 complete (ACR exists, GHA shared MI exists with AcrPush).

**Files:**
- Create: `.github/workflows/_azure-auth.yml`, `.github/workflows/image-build.yml`
- Modify: `src/dsv-app/Dockerfile`, `src/dsv-db/Dockerfile` — ensure they build cleanly. (Likely no changes needed; verify.)

- [ ] **Step 1: Verify Dockerfile builds locally**

```bash
cd /home/sam/SCM/github/DineSafeViz/src/dsv-app
docker build -t dsv-app:test .
docker image rm dsv-app:test
```

- [ ] **Step 2: Write `_azure-auth.yml` reusable composite**

Create `.github/workflows/_azure-auth.yml`:

```yaml
name: _azure-auth (reusable)

on:
  workflow_call:
    inputs:
      identity:
        description: 'Which identity to use: shared | prod | staging'
        type: string
        required: true
      environment:
        description: 'GitHub environment to claim (only for env-gated identities)'
        type: string
        required: false

permissions:
  id-token: write
  contents: read

jobs:
  auth:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Map identity to client ID
        id: client
        run: |
          case "${{ inputs.identity }}" in
            prod)    echo "id=${{ vars.AZURE_CLIENT_ID_PROD }}"    >> $GITHUB_OUTPUT ;;
            staging) echo "id=${{ vars.AZURE_CLIENT_ID_STAGING }}" >> $GITHUB_OUTPUT ;;
            shared)  echo "id=${{ vars.AZURE_CLIENT_ID_SHARED }}"  >> $GITHUB_OUTPUT ;;
            *) echo "Unknown identity"; exit 1 ;;
          esac
      - uses: azure/login@v2
        with:
          client-id: ${{ steps.client.outputs.id }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

(Note: workflow_call composites in GHA do not natively pass auth state to caller — callers will reuse `azure/login@v2` directly. The shared file documents the pattern; we may inline rather than `uses:`. Decision in Step 5.)

- [ ] **Step 3: Write `image-build.yml`**

Create `.github/workflows/image-build.yml`:

```yaml
name: image-build

on:
  push:
    branches: [main]
    paths:
      - 'src/dsv-app/**'
      - 'src/dsv-db/**'
      - '.github/workflows/image-build.yml'
    tags:
      - 'v*'
  pull_request:
    paths:
      - 'src/dsv-app/**'
      - 'src/dsv-db/**'
      - '.github/workflows/image-build.yml'
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  REGISTRY: ${{ vars.ACR_LOGIN_SERVER }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      tag_sha: ${{ steps.tags.outputs.sha }}
      tag_semver: ${{ steps.tags.outputs.semver }}
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID_SHARED }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: ACR login
        run: az acr login --name "${{ vars.ACR_LOGIN_SERVER }}" --expose-token >/dev/null
        # Alternative: configure docker via az acr login (handles the auth)

      - name: Compute image tags
        id: tags
        run: |
          SHA="sha-$(echo ${{ github.sha }} | cut -c1-7)"
          echo "sha=$SHA" >> $GITHUB_OUTPUT
          if [[ "${{ github.ref_type }}" == "tag" ]]; then
            echo "semver=${{ github.ref_name }}" >> $GITHUB_OUTPUT
          else
            echo "semver=" >> $GITHUB_OUTPUT
          fi

      - name: Build and push app image
        run: |
          docker buildx build \
            --push \
            --platform linux/amd64 \
            -t ${{ env.REGISTRY }}/dinesafeviz/app:${{ steps.tags.outputs.sha }} \
            $( [[ "${{ github.ref_name }}" == "main" ]] && echo "-t ${{ env.REGISTRY }}/dinesafeviz/app:latest" ) \
            $( [[ -n "${{ steps.tags.outputs.semver }}" ]] && echo "-t ${{ env.REGISTRY }}/dinesafeviz/app:${{ steps.tags.outputs.semver }}" ) \
            -f src/dsv-app/Dockerfile \
            src/dsv-app/

      - name: Build and push init-db image
        run: |
          docker buildx build \
            --push \
            --platform linux/amd64 \
            -t ${{ env.REGISTRY }}/dinesafeviz/init-db:${{ steps.tags.outputs.sha }} \
            $( [[ "${{ github.ref_name }}" == "main" ]] && echo "-t ${{ env.REGISTRY }}/dinesafeviz/init-db:latest" ) \
            $( [[ -n "${{ steps.tags.outputs.semver }}" ]] && echo "-t ${{ env.REGISTRY }}/dinesafeviz/init-db:${{ steps.tags.outputs.semver }}" ) \
            -f src/dsv-db/Dockerfile \
            src/dsv-db/
```

- [ ] **Step 4: Test workflow on a branch push**

```bash
git checkout -b test/image-build-bootstrap
git commit --allow-empty -m "test: trigger image-build workflow"
git push -u origin test/image-build-bootstrap
gh run watch
# Expected: PR run completes; ACR contains sha-tagged images.
```

- [ ] **Step 5: Verify images in ACR**

```bash
az acr repository list --name "$(terraform -chdir=infra/terraform/azure-shared output -raw acr_login_server | cut -d. -f1)"
# Expected output: ["dinesafeviz/app", "dinesafeviz/init-db"]
```

- [ ] **Step 6: Add `terraform-shared.yml` for future shared-infra applies**

Create `.github/workflows/terraform-shared.yml`:

```yaml
name: terraform-shared

on:
  push:
    branches: [main]
    paths: ['infra/terraform/azure-shared/**']
  pull_request:
    paths: ['infra/terraform/azure-shared/**']
  workflow_dispatch:
    inputs:
      action:
        type: choice
        options: [plan, apply]
        default: plan

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra/terraform/azure-shared
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.x"
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID_SHARED }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - run: terraform init
      - run: terraform plan -no-color -out=tfplan
      - if: ${{ github.event_name == 'pull_request' }}
        name: Post plan to PR
        run: terraform show -no-color tfplan > $GITHUB_STEP_SUMMARY
      - if: ${{ (github.ref == 'refs/heads/main' && github.event_name == 'push') || inputs.action == 'apply' }}
        run: terraform apply -auto-approve tfplan
```

- [ ] **Step 7: Commit and merge image-build workflow**

```bash
git add .github/workflows/_azure-auth.yml .github/workflows/image-build.yml .github/workflows/terraform-shared.yml
git commit -m "ci: add image-build and terraform-shared workflows

- image-build: pushes sha/semver/latest tagged images to ACR via OIDC
- terraform-shared: plans on PR, applies on main merge or dispatch
- both use id-gha-dsv-shared-eus2 via federated identity"
git push
```

---

## Epic 4 — Staging Azure infrastructure (Terraform)

**Goal:** Provision the staging-environment Azure resources: VNet, AKS cluster (stopped initially? actually created in running state, immediately stopped via Step 14), Key Vault, WAL storage account, workload-identity managed identities, all role assignments.

**Prereq:** Epic 2 complete (shared infra exists; GHA staging MI exists).

**Files:**
- Create: `infra/terraform/azure-staging/{backend.tf,main.tf,network.tf,aks.tf,key_vault.tf,storage_wal.tf,managed_identities.tf,role_assignments.tf,variables.tf,outputs.tf,terraform.tfvars.example}`

- [ ] **Step 1: Write `backend.tf`**

Create `infra/terraform/azure-staging/backend.tf`:

```hcl
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    random  = { source = "hashicorp/random",  version = "~> 3.6" }
  }
  backend "azurerm" {
    resource_group_name  = "rg-dsv-shared-eus2"
    storage_account_name = "stdsvtfsteus2<RND>"
    container_name       = "tfstate"
    key                  = "azure-staging.tfstate"
    use_azuread_auth     = true
  }
}
```

- [ ] **Step 2: Write `main.tf`**

```hcl
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

data "azurerm_client_config" "current" {}

# Reference shared resources by data source
data "azurerm_resource_group" "shared" {
  name = "rg-dsv-shared-eus2"
}

data "azurerm_dns_zone" "main" {
  name                = "dinesafeviz.com"
  resource_group_name = data.azurerm_resource_group.shared.name
}

data "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = data.azurerm_resource_group.shared.name
}

data "azurerm_user_assigned_identity" "gha_staging" {
  name                = "id-gha-dsv-stg-eus2"
  resource_group_name = data.azurerm_resource_group.shared.name
}

data "azurerm_log_analytics_workspace" "main" {
  name                = "log-dsv-shared-eus2"
  resource_group_name = data.azurerm_resource_group.shared.name
}

locals {
  env      = "stg"
  region   = "eus2"
  workload = "dsv"
  tags = {
    workload    = "dinesafeviz"
    environment = "staging"
    managed_by  = "terraform"
    cost_center = "personal"
    owner       = "im-kenough"
    repo        = "github.com/im-kenough/DineSafeViz"
  }
}

resource "random_string" "suffix" {
  length  = 4
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.workload}-${local.env}-${local.region}"
  location = "eastus2"
  tags     = local.tags
}
```

- [ ] **Step 3: Write `network.tf`**

```hcl
resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.workload}-${local.env}-${local.region}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = ["10.60.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "aks_nodes" {
  name                 = "snet-${local.workload}-aksnodes-${local.env}-${local.region}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.60.0.0/22"]
}

resource "azurerm_subnet" "aks_pods" {
  name                 = "snet-${local.workload}-akspods-${local.env}-${local.region}"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.60.4.0/22"]
  delegation {
    name = "aks-delegation"
    service_delegation {
      name    = "Microsoft.ContainerService/managedClusters"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_public_ip" "ingress" {
  name                = "pip-${local.workload}-ingress-${local.env}-${local.region}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
  tags                = local.tags
}
```

- [ ] **Step 4: Write `managed_identities.tf`**

```hcl
resource "azurerm_user_assigned_identity" "aks_controlplane" {
  name                = "id-aks-controlplane-${local.env}-${local.region}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "cnpg" {
  name                = "id-aks-cnpg-${local.env}-${local.region}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "certmgr" {
  name                = "id-aks-certmgr-${local.env}-${local.region}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "kvcsi" {
  name                = "id-aks-kvcsi-${local.env}-${local.region}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}
```

- [ ] **Step 5: Write `aks.tf`**

```hcl
resource "azurerm_kubernetes_cluster" "main" {
  name                = "aks-${local.workload}-${local.env}-${local.region}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  dns_prefix          = "aks-${local.workload}-${local.env}"
  sku_tier            = "Free"
  kubernetes_version  = "1.30"  # bump deliberately
  node_resource_group = "rg-${local.workload}-${local.env}-${local.region}-nodes"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks_controlplane.id]
  }

  workload_identity_enabled = true
  oidc_issuer_enabled       = true

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_policy      = "cilium"
    network_dataplane   = "cilium"
    service_cidr        = "172.16.0.0/16"
    dns_service_ip      = "172.16.0.10"
    load_balancer_sku   = "standard"
  }

  default_node_pool {
    name                 = "syspool"
    vm_size              = "Standard_B2s"
    min_count            = 1
    max_count            = 2
    auto_scaling_enabled = true
    zones                = ["1", "2", "3"]
    vnet_subnet_id       = azurerm_subnet.aks_nodes.id
    pod_subnet_id        = azurerm_subnet.aks_pods.id
    only_critical_addons_enabled = false  # Phase 1: allow non-system pods on syspool for CNPG
    tags = local.tags
  }

  oms_agent {
    log_analytics_workspace_id      = data.azurerm_log_analytics_workspace.main.id
    msi_auth_for_monitoring_enabled = true
  }

  azure_active_directory_role_based_access_control {
    azure_rbac_enabled = true
    tenant_id          = data.azurerm_client_config.current.tenant_id
  }

  tags = local.tags
}

resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "usrpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_B2s"
  min_count             = 1
  max_count             = 3
  auto_scaling_enabled  = true
  zones                 = ["1", "2", "3"]
  vnet_subnet_id        = azurerm_subnet.aks_nodes.id
  pod_subnet_id         = azurerm_subnet.aks_pods.id

  priority        = "Spot"
  eviction_policy = "Delete"
  spot_max_price  = -1   # cap at on-demand price

  node_taints = ["kubernetes.azure.com/scalesetpriority=spot:NoSchedule"]
  node_labels = { "kubernetes.azure.com/scalesetpriority" = "spot" }

  tags = local.tags
}
```

- [ ] **Step 6: Write `key_vault.tf`**

```hcl
resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.workload}-${local.env}-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  soft_delete_retention_days = 90
  purge_protection_enabled   = true
  tags                       = local.tags
}

resource "random_password" "analytics_admin" {
  length  = 32
  special = true
}

resource "random_password" "analytics_secret_key" {
  length  = 64
  special = false
}

# Grant the operator (whoever runs Terraform) Secrets Officer to populate the vault
resource "azurerm_role_assignment" "kv_operator" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_key_vault_secret" "analytics_admin_password" {
  name         = "analytics-admin-password"
  value        = random_password.analytics_admin.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_operator]
}

resource "azurerm_key_vault_secret" "analytics_secret_key" {
  name         = "analytics-secret-key"
  value        = random_password.analytics_secret_key.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_operator]
}
```

- [ ] **Step 7: Write `storage_wal.tf`**

```hcl
resource "azurerm_storage_account" "wal" {
  name                            = "stdsvwal${local.env}eus2${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"   # staging doesn't need DR
  account_kind                    = "StorageV2"
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  tags                            = local.tags
}

resource "azurerm_storage_container" "wal" {
  name                  = "cnpg-wal-stg"
  storage_account_name  = azurerm_storage_account.wal.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "basebackups" {
  name                  = "cnpg-basebackups-stg"
  storage_account_name  = azurerm_storage_account.wal.name
  container_access_type = "private"
}
```

- [ ] **Step 8: Write `role_assignments.tf`**

```hcl
# AKS control plane: AcrPull on ACR
resource "azurerm_role_assignment" "aks_acrpull" {
  scope                = data.azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aks_controlplane.principal_id
}

# AKS control plane: Network Contributor on VNet
resource "azurerm_role_assignment" "aks_network_contributor" {
  scope                = azurerm_virtual_network.main.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.main.identity[0].principal_id
}

# CNPG MI: Storage Blob Data Contributor on WAL storage
resource "azurerm_role_assignment" "cnpg_blob_contributor" {
  scope                = azurerm_storage_account.wal.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.cnpg.principal_id
}

# cert-manager MI: DNS Zone Contributor on shared zone
resource "azurerm_role_assignment" "certmgr_dns" {
  scope                = data.azurerm_dns_zone.main.id
  role_definition_name = "DNS Zone Contributor"
  principal_id         = azurerm_user_assigned_identity.certmgr.principal_id
}

# CSI Secrets Store MI: Key Vault Secrets User on KV
resource "azurerm_role_assignment" "kvcsi_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.kvcsi.principal_id
}

# GHA staging MI: AKS Contributor on this RG
resource "azurerm_role_assignment" "gha_aks_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Azure Kubernetes Service Contributor"
  principal_id         = data.azurerm_user_assigned_identity.gha_staging.principal_id
}

# Federated identity credentials for workload identities (cluster OIDC issuer → MI)
resource "azurerm_federated_identity_credential" "cnpg" {
  name                = "cnpg-workload-identity"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.cnpg.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject             = "system:serviceaccount:dsv-app:pg-dsv-stg"
}

resource "azurerm_federated_identity_credential" "certmgr" {
  name                = "certmgr-workload-identity"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.certmgr.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject             = "system:serviceaccount:cert-manager:cert-manager"
}

resource "azurerm_federated_identity_credential" "kvcsi" {
  name                = "kvcsi-workload-identity"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.kvcsi.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject             = "system:serviceaccount:kube-system:secrets-store-csi-driver"
}
```

- [ ] **Step 9: Write `variables.tf` and `outputs.tf`**

```hcl
# variables.tf
variable "acr_name" {
  type        = string
  description = "Name of the shared ACR (without .azurecr.io)"
}
```

```hcl
# outputs.tf
output "aks_cluster_name" { value = azurerm_kubernetes_cluster.main.name }
output "aks_resource_group" { value = azurerm_resource_group.main.name }
output "aks_oidc_issuer_url" { value = azurerm_kubernetes_cluster.main.oidc_issuer_url }
output "cnpg_client_id" { value = azurerm_user_assigned_identity.cnpg.client_id }
output "certmgr_client_id" { value = azurerm_user_assigned_identity.certmgr.client_id }
output "kvcsi_client_id" { value = azurerm_user_assigned_identity.kvcsi.client_id }
output "ingress_public_ip" { value = azurerm_public_ip.ingress.ip_address }
output "key_vault_name" { value = azurerm_key_vault.main.name }
output "wal_storage_account_name" { value = azurerm_storage_account.wal.name }
```

- [ ] **Step 10: Apply staging Terraform**

```bash
cd infra/terraform/azure-staging
# Substitute the actual ACR name from shared outputs.
ACR_NAME=$(terraform -chdir=../azure-shared output -raw acr_login_server | cut -d. -f1)
cat > terraform.tfvars <<EOF
acr_name = "${ACR_NAME}"
EOF
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

- [ ] **Step 11: Create staging DNS A record**

Inside `infra/terraform/azure-shared/`, add to `dns_zone.tf` (or a new `dns_records.tf`):

```hcl
data "azurerm_public_ip" "stg_ingress" {
  name                = "pip-dsv-ingress-stg-eus2"
  resource_group_name = "rg-dsv-stg-eus2"
}

resource "azurerm_dns_a_record" "stg" {
  name                = "stg"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.shared.name
  ttl                 = 300
  records             = [data.azurerm_public_ip.stg_ingress.ip_address]
}
```

```bash
cd infra/terraform/azure-shared
terraform plan -out=tfplan
terraform apply tfplan
```

- [ ] **Step 12: Verify cluster reachability**

```bash
az aks get-credentials -g rg-dsv-stg-eus2 -n aks-dsv-stg-eus2 --overwrite-existing
kubectl get nodes -o wide
# Expected: 2 nodes (1 syspool + 1 usrpool)
```

- [ ] **Step 13: Commit staging Terraform**

```bash
git add infra/terraform/azure-staging/ infra/terraform/azure-shared/dns_zone.tf  # if records added there
git commit -m "infra: provision staging Azure resources (AKS, VNet, KV, WAL storage, MIs)"
```

---

## Epic 5 — Cluster bootstrap Helm chart

**Goal:** Build `infra/helm/cluster-bootstrap` to install CNPG operator, ingress-nginx, cert-manager, CSI Secrets Store Driver + Azure provider, plus a custom StorageClass and ClusterIssuer.

**Prereq:** Epic 4 complete (staging cluster reachable via kubectl).

**Files:**
- Create: `infra/helm/cluster-bootstrap/{Chart.yaml,values.yaml,values-staging.yaml,values-prod.yaml,templates/*}`

- [ ] **Step 1: Initialize chart skeleton**

```bash
mkdir -p infra/helm/cluster-bootstrap/templates
cd infra/helm/cluster-bootstrap
```

- [ ] **Step 2: Write `Chart.yaml`**

```yaml
apiVersion: v2
name: cluster-bootstrap
description: AKS cluster-level dependencies (CNPG, ingress-nginx, cert-manager, CSI driver, StorageClass, ClusterIssuer)
type: application
version: 0.1.0
appVersion: "1.0.0"

dependencies:
  - name: cloudnative-pg
    version: "0.23.x"
    repository: https://cloudnative-pg.github.io/charts
  - name: ingress-nginx
    version: "4.x.x"
    repository: https://kubernetes.github.io/ingress-nginx
    alias: nginx
  - name: cert-manager
    version: "1.16.x"
    repository: https://charts.jetstack.io
  - name: csi-secrets-store-provider-azure
    version: "1.5.x"
    repository: https://azure.github.io/secrets-store-csi-driver-provider-azure/charts
```

- [ ] **Step 3: Write `values.yaml` (defaults)**

```yaml
ingressPublicIp: ""        # set per env

certmgr:
  workloadIdentityClientId: ""  # set per env
  dnsZoneRG: rg-dsv-shared-eus2
  dnsZoneName: dinesafeviz.com
  azureSubscriptionId: ""
  azureTenantId: ""
  acmeEmail: ""             # set per env (Let's Encrypt account email)

cloudnative-pg:
  config:
    data: {}
  nodeSelector:
    kubernetes.azure.com/agentpool: syspool

nginx:
  controller:
    replicaCount: 1
    nodeSelector:
      kubernetes.azure.com/agentpool: syspool
    service:
      loadBalancerIP: ""    # set per env
      annotations:
        service.beta.kubernetes.io/azure-load-balancer-resource-group: ""

cert-manager:
  installCRDs: true
  nodeSelector:
    kubernetes.azure.com/agentpool: syspool
  serviceAccount:
    annotations:
      azure.workload.identity/client-id: ""  # set per env

csi-secrets-store-provider-azure:
  secrets-store-csi-driver:
    syncSecret:
      enabled: true
    enableSecretRotation: true
```

- [ ] **Step 4: Write `values-staging.yaml`**

```yaml
ingressPublicIp: "<staging public IP from terraform output>"

certmgr:
  workloadIdentityClientId: "<certmgr_client_id from azure-staging>"
  acmeEmail: "admin-2ndshap@protonmail.com"
  azureSubscriptionId: "<sub-id>"
  azureTenantId: "<tenant-id>"

nginx:
  controller:
    service:
      loadBalancerIP: "<staging public IP>"
      annotations:
        service.beta.kubernetes.io/azure-load-balancer-resource-group: "rg-dsv-stg-eus2-nodes"

cert-manager:
  serviceAccount:
    annotations:
      azure.workload.identity/client-id: "<certmgr_client_id>"
```

- [ ] **Step 5: Write `templates/namespaces.yaml`**

```yaml
{{- range $ns := list "cnpg-system" "ingress-nginx" "cert-manager" "dsv-app" }}
apiVersion: v1
kind: Namespace
metadata:
  name: {{ $ns }}
  labels:
    workload: dinesafeviz
---
{{- end }}
```

- [ ] **Step 6: Write `templates/storageclass-standard-ssd.yaml`**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: dsv-standard-ssd
provisioner: disk.csi.azure.com
parameters:
  skuname: StandardSSD_LRS
  cachingmode: ReadOnly
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

- [ ] **Step 7: Write `templates/clusterissuer-letsencrypt.yaml`**

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: {{ .Values.certmgr.acmeEmail }}
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - dns01:
          azureDNS:
            subscriptionID: {{ .Values.certmgr.azureSubscriptionId }}
            tenantID: {{ .Values.certmgr.azureTenantId }}
            resourceGroupName: {{ .Values.certmgr.dnsZoneRG }}
            hostedZoneName: {{ .Values.certmgr.dnsZoneName }}
            managedIdentity:
              clientID: {{ .Values.certmgr.workloadIdentityClientId }}
```

- [ ] **Step 8: Helm install on staging**

```bash
cd infra/helm/cluster-bootstrap
helm dependency update
helm upgrade --install cluster-bootstrap . \
  --namespace kube-system \
  --create-namespace \
  --values values-staging.yaml \
  --wait \
  --timeout 15m
```

Expected: CNPG operator pod in `cnpg-system` Ready; ingress-nginx controller pod with LoadBalancer IP matching `pip-dsv-ingress-stg-eus2`; cert-manager pods Ready; CSI driver DaemonSet running on all nodes.

- [ ] **Step 9: Sanity-check ClusterIssuer**

```bash
kubectl get clusterissuer letsencrypt-prod
# Expected: STATUS Ready=True
```

- [ ] **Step 10: Commit bootstrap chart**

```bash
git add infra/helm/cluster-bootstrap/
git commit -m "infra: add cluster-bootstrap Helm chart for CNPG/nginx/cert-manager/CSI"
```

---

## Epic 6 — DineSafeViz app Helm chart

**Goal:** Build `infra/helm/dinesafeviz` chart containing all application templates (Postgres Cluster CR, Deployments, Services, Ingresses, NetworkPolicies, SecretProviderClass, init Jobs).

**Prereq:** Epic 5 complete (operator + CRDs installed in staging cluster).

**Files:**
- Create: `infra/helm/dinesafeviz/{Chart.yaml,values.yaml,values-staging.yaml,values-prod.yaml,templates/*}`

This epic produces many template files. Reference the spec section "Helm chart contents" for the full inventory.

- [ ] **Step 1: Chart skeleton**

```bash
mkdir -p infra/helm/dinesafeviz/templates/tests
cd infra/helm/dinesafeviz
```

- [ ] **Step 2: Write `Chart.yaml`**

```yaml
apiVersion: v2
name: dinesafeviz
description: DineSafeViz Flask web app + analytics dashboard + CloudNativePG database
type: application
version: 0.1.0
appVersion: "0.4.0"
keywords: [dinesafeviz, flask, postgres, analytics]
maintainers:
  - name: im-kenough
```

- [ ] **Step 3: Write `values.yaml`** (use the skeleton from spec Section 5 — full block included verbatim)

(Copy from spec; substitute `analytics:` for `grafana:` per rename.)

- [ ] **Step 4: Write `values-staging.yaml` and `values-prod.yaml`**

(Copy from spec section "values-prod.yaml" / "values-staging.yaml" — fill placeholders with actual output values from azure-shared and azure-staging.)

- [ ] **Step 5: Write `templates/_helpers.tpl`**

```yaml
{{- define "dinesafeviz.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride }}
{{- else }}
{{- printf "%s" .Release.Name }}
{{- end }}
{{- end }}

{{- define "dinesafeviz.labels" -}}
app.kubernetes.io/name: {{ include "dinesafeviz.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
workload: dinesafeviz
environment: {{ .Values.environment }}
{{- end }}
```

- [ ] **Step 6: Write `templates/serviceaccount-*.yaml`**

```yaml
# templates/serviceaccount-app.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dsv-app
  namespace: {{ .Release.Namespace }}
  labels: {{- include "dinesafeviz.labels" . | nindent 4 }}
---
# templates/serviceaccount-analytics.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dsv-analytics
  namespace: {{ .Release.Namespace }}
  labels: {{- include "dinesafeviz.labels" . | nindent 4 }}
```

- [ ] **Step 7: Write `templates/postgres-cluster.yaml`**

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: {{ .Values.postgres.clusterName }}
  namespace: {{ .Release.Namespace }}
  labels: {{- include "dinesafeviz.labels" . | nindent 4 }}
spec:
  instances: {{ .Values.postgres.instances }}
  imageName: {{ .Values.postgres.image }}
  primaryUpdateStrategy: unsupervised
  serviceAccountTemplate:
    metadata:
      annotations:
        azure.workload.identity/client-id: {{ .Values.postgres.workloadIdentity.serviceAccountAnnotation }}
      labels:
        azure.workload.identity/use: "true"
  storage:
    size: {{ .Values.postgres.storage.size }}
    storageClass: {{ .Values.postgres.storage.storageClass }}
  resources:
    requests:
      cpu: {{ .Values.postgres.resources.requests.cpu }}
      memory: {{ .Values.postgres.resources.requests.memory }}
    limits:
      cpu: {{ .Values.postgres.resources.limits.cpu }}
      memory: {{ .Values.postgres.resources.limits.memory }}
  affinity:
    nodeSelector:
      kubernetes.azure.com/agentpool: syspool
    topologyKey: topology.kubernetes.io/zone
    podAntiAffinityType: preferred
  monitoring:
    enablePodMonitor: true
  bootstrap:
    initdb:
      database: {{ .Values.postgres.database }}
      owner: {{ .Values.postgres.owner }}
      postInitApplicationSQLRefs:
        configMapRefs:
          - name: dsv-pg-init-sql
            key: init.sql
  backup:
    barmanObjectStore:
      destinationPath: {{ .Values.postgres.backup.destinationPath }}
      azureCredentials:
        inheritFromAzureAD: true
      wal:
        compression: gzip
        maxParallel: 4
      data:
        compression: gzip
        jobs: 2
    retentionPolicy: {{ .Values.postgres.backup.retentionPolicy }}
```

- [ ] **Step 8: Write `templates/postgres-scheduledbackup.yaml`**

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: {{ .Values.postgres.clusterName }}-daily-backup
  namespace: {{ .Release.Namespace }}
spec:
  schedule: {{ .Values.postgres.backup.scheduledBackup.schedule | quote }}
  backupOwnerReference: self
  cluster:
    name: {{ .Values.postgres.clusterName }}
```

- [ ] **Step 9: Write `templates/postgres-init-configmap.yaml`** — references `src/dsv-db/init.sql`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dsv-pg-init-sql
  namespace: {{ .Release.Namespace }}
data:
  init.sql: |
{{ .Files.Get "files/init.sql" | indent 4 }}
```

The Helm chart needs `infra/helm/dinesafeviz/files/init.sql` (copy from `src/dsv-db/init.sql` and keep in sync via a Makefile target, or use Helm `.Files.Glob`).

- [ ] **Step 10: Write `templates/secretproviderclass.yaml`**

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: dsv-keyvault-secrets
  namespace: {{ .Release.Namespace }}
spec:
  provider: azure
  parameters:
    keyvaultName: {{ .Values.secretProviderClass.keyvaultName }}
    tenantId: {{ .Values.secretProviderClass.tenantId }}
    clientID: {{ .Values.secretProviderClass.clientId }}
    objects: |
      array:
      {{- range .Values.secretProviderClass.secrets }}
        - |
          objectName: {{ .objectName }}
          objectType: secret
      {{- end }}
  secretObjects:
    {{- range .Values.secretProviderClass.secrets }}
    - secretName: {{ .name }}
      type: Opaque
      data:
        - objectName: {{ .objectName }}
          key: value
    {{- end }}
```

- [ ] **Step 11: Write app Deployment + Service + Ingress + Certificate**

```yaml
# templates/app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dsv-app
  namespace: {{ .Release.Namespace }}
  labels: {{- include "dinesafeviz.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.app.replicas }}
  selector:
    matchLabels:
      app.kubernetes.io/name: dsv-app
  template:
    metadata:
      labels:
        app.kubernetes.io/name: dsv-app
    spec:
      serviceAccountName: dsv-app
      nodeSelector:
        kubernetes.azure.com/scalesetpriority: spot
      tolerations:
        - key: kubernetes.azure.com/scalesetpriority
          operator: Equal
          value: spot
          effect: NoSchedule
      containers:
        - name: app
          image: "{{ .Values.image.registry }}/{{ .Values.app.image.repository }}:{{ .Values.app.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - containerPort: 5000
          envFrom:
            - secretRef:
                name: {{ .Values.postgres.clusterName }}-app
          env:
            - name: DB_HOST
              value: {{ .Values.postgres.clusterName }}-rw
            - name: DB_PORT
              value: "5432"
            - name: DB_NAME
              value: {{ .Values.postgres.database }}
          readinessProbe:
            httpGet:
              path: /
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 10
          resources: {{ toYaml .Values.app.resources | nindent 12 }}
```

```yaml
# templates/app-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: dsv-app
  namespace: {{ .Release.Namespace }}
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: dsv-app
  ports:
    - port: 5000
      targetPort: 5000
```

```yaml
# templates/app-ingress.yaml
{{- if .Values.app.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dsv-app
  namespace: {{ .Release.Namespace }}
  annotations:
    cert-manager.io/cluster-issuer: {{ .Values.certManager.clusterIssuer }}
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: {{ .Values.app.ingress.className }}
  tls:
    - hosts:
        - {{ .Values.app.ingress.host }}
      secretName: dsv-app-tls
  rules:
    - host: {{ .Values.app.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: dsv-app
                port:
                  number: 5000
{{- end }}
```

- [ ] **Step 12: Write analytics Deployment + Service + PVC + ConfigMaps**

(Pattern equivalent to app. Mount analytics PVC at `/var/lib/grafana`, env var `GF_SECURITY_ADMIN_PASSWORD` from synced KV-mounted Secret, provisioning ConfigMaps mounted at `/etc/grafana/provisioning/`.)

- [ ] **Step 13: Write NetworkPolicy templates**

Eight NetworkPolicy resources per spec Section 5 inventory. Key example:

```yaml
# templates/networkpolicy-default-deny.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: {{ .Release.Namespace }}
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

(Remaining policies follow the spec.)

- [ ] **Step 14: Write init Job templates as Helm hooks**

```yaml
# templates/init-db-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: dsv-init-db
  namespace: {{ .Release.Namespace }}
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "10"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: OnFailure
      serviceAccountName: dsv-app
      nodeSelector:
        kubernetes.azure.com/scalesetpriority: spot
      tolerations:
        - key: kubernetes.azure.com/scalesetpriority
          operator: Equal
          value: spot
          effect: NoSchedule
      initContainers:
        - name: wait-for-pg
          image: postgres:17
          command:
            - sh
            - -c
            - |
              until pg_isready -h {{ .Values.postgres.clusterName }}-rw -U $POSTGRES_USER; do
                echo "waiting for postgres"; sleep 2;
              done
          envFrom:
            - secretRef:
                name: {{ .Values.postgres.clusterName }}-app
      containers:
        - name: init-db
          image: "{{ .Values.image.registry }}/{{ .Values.initJobs.initDb.image.repository }}:{{ .Values.initJobs.initDb.image.tag }}"
          envFrom:
            - secretRef:
                name: {{ .Values.postgres.clusterName }}-app
          env:
            - name: DB_HOST
              value: {{ .Values.postgres.clusterName }}-rw
            - name: DB_NAME
              value: {{ .Values.postgres.database }}
```

- [ ] **Step 15: Write `helmfile.yaml`**

Create `infra/helmfile.yaml` per spec Section 5.

- [ ] **Step 16: Helm install on staging**

```bash
helmfile --environment staging -l app=dsv sync --set app.image.tag=sha-<7char-from-image-build>
```

- [ ] **Step 17: Commit app chart**

```bash
git add infra/helm/dinesafeviz/ infra/helmfile.yaml
git commit -m "infra: add dinesafeviz Helm chart + Helmfile orchestrator"
```

---

## Epic 7 — AKS lifecycle GHA workflows

**Goal:** `aks-up.yml`, `aks-down.yml`, `aks-scale.yml`, `app-deploy.yml` driving cluster lifecycle from GitHub.

**Prereq:** Epic 4 complete (cluster exists).

**Files:**
- Create: `.github/workflows/{aks-up,aks-down,aks-scale,app-deploy}.yml`

- [ ] **Step 1-4: Write each workflow per spec Section 6**

(Each workflow file ~50-80 lines. Pattern: `workflow_dispatch` triggers, env-matched identity via composite, `az aks ...` or `helmfile ...` commands.)

- [ ] **Step 5: Commit workflows**

```bash
git add .github/workflows/aks-*.yml .github/workflows/app-deploy.yml
git commit -m "ci: add AKS lifecycle workflows (aks-up/down/scale, app-deploy)"
```

---

## Epic 8 — Staging end-to-end validation

**Goal:** Run the full cycle on staging and prove the pipeline works.

**Prereq:** Epics 1-7 complete.

- [ ] **Step 1: Bring staging up**

Trigger `aks-up.yml` for staging via GHA UI. Wait for completion (~10-15 min).

- [ ] **Step 2: Verify cluster state**

```bash
az aks get-credentials -g rg-dsv-stg-eus2 -n aks-dsv-stg-eus2 --overwrite-existing
kubectl get nodes
kubectl get pods -A
kubectl get cluster -n dsv-app
kubectl get certificate -n dsv-app
```

Expected: nodes Ready, all system pods Running, CNPG Cluster `pg-dsv-stg` in `Cluster in healthy state`, certificate `dsv-app-tls` Ready.

- [ ] **Step 3: Verify TLS**

```bash
curl -I https://stg.dinesafeviz.com/
# Expected: HTTP/2 200, valid Let's Encrypt cert
```

- [ ] **Step 4: Verify data**

```bash
curl -s https://stg.dinesafeviz.com/ | grep -i 'inspection'
# Expected: home page shows DB counters (years, total inspections)
```

- [ ] **Step 5: Bring staging down**

Trigger `aks-down.yml` for staging.

- [ ] **Step 6: Verify cost (after 24h)**

```bash
az consumption usage list --start-date $(date -d '24 hours ago' +%Y-%m-%d) --end-date $(date +%Y-%m-%d) | jq '.[] | select(.instanceName | contains("aks-dsv-stg")) | {resource: .instanceName, cost: .pretaxCost}'
```

---

## Epic 9 — Prod Azure infrastructure (Terraform)

**Goal:** Mirror Epic 4 structure for prod environment.

**Files:** Identical structure to `infra/terraform/azure-staging/` but in `infra/terraform/azure-prod/`. Key differences:
- `env = "prod"`, VNet `10.50.0.0/16`, WAL storage GRS (not LRS), PVC size 32Gi.
- `terraform-prod.yml` workflow with `workflow_dispatch` + `environment: prod` for required-reviewer approval.

(Tasks structurally identical to Epic 4 with the differences above.)

---

## Epic 10 — Prod deployment + DNS cutover

**Goal:** Run the full validated stack on prod.

- [ ] **Step 1: Trigger `aks-up.yml` for prod**

Manual workflow dispatch with `cluster=prod` + reviewer approval.

- [ ] **Step 2: Tag release** `git tag v0.4.0 && git push origin v0.4.0` to trigger image build with `:v0.4.0` tag.

- [ ] **Step 3: Trigger `app-deploy.yml`** with `env=prod`, `tag=v0.4.0`, `confirm=DEPLOY-PROD-v0.4.0`. Approve via GH env.

- [ ] **Step 4: Add prod DNS A record (in `azure-shared/dns_zone.tf`)** — apply via `terraform-shared.yml`.

- [ ] **Step 5: Verify cert + endpoint** `curl -I https://dinesafeviz.com/`.

- [ ] **Step 6: Bring prod down** `aks-down.yml`.

---

## Epic 11 — Observability hookup

- [ ] Add Azure Monitor availability test for `https://dinesafeviz.com/`.
- [ ] Add KQL alerts on Postgres pod restart count, AKS cluster running > 12h, cert age < 60d remaining.
- [ ] Add Azure budget alert at $40/mo (80% of $50/mo lean tier cap).
- [ ] Commit Terraform additions.

---

## Epic 12 — Scheduled operational workflows

- [ ] Write `cert-renewal-heartbeat.yml` (monthly schedule).
- [ ] Write `acr-cleanup.yml` (weekly schedule, purge untagged > 30d).
- [ ] Write `db-backup-verify.yml` (weekly schedule, check basebackup age in blob).
- [ ] Commit and verify first scheduled run.

---

## Epic 13 — Documentation refresh

- [ ] Create `docs/how-to/7-aks-setup.md` — first-time AKS setup walkthrough.
- [ ] Create `docs/how-to/8-aks-operations.md` — runbooks RB-01 through RB-16.
- [ ] Update `README.md` evolution section: add `v0.4.0 — AKS deployment`.
- [ ] Update `docs/ref/arch/arch-iac.md`, `arch-net.md`, `arch-security.md`, `arch-dr.md` with the Azure architecture.
- [ ] Commit docs pass.

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by epic(s) |
|---|---|
| Summary, Goals, Non-goals | Plan header |
| Decision matrix | All Epics implement it |
| Topology | Epics 2, 4, 9 |
| Naming convention + full account inventory | Epics 2, 4, 9 (Terraform module structure encodes it) |
| Network, DNS, TLS | Epics 4, 5, 9, 10 |
| Identity, secrets, ACR | Epics 2, 4, 5, 9 |
| Database layer (CNPG) | Epics 4, 6 |
| Helm chart + app deployment | Epics 5, 6 |
| GHA workflows | Epics 1, 3, 7, 12 |
| Failure modes + runbooks | Epic 13 |
| Observability | Epic 11 |
| Cost summary | (Implicit — validated by Epic 8 cost check) |
| Roadmap | Documented in spec; not implemented in Phase 1 |
| Implementation order | Plan epic ordering mirrors spec's 14-step phasing |

**Placeholder scan:** Spot-checked for "TBD" / "TODO" / "implement later" — none in the plan body. The `<RND>` placeholders are explicitly documented as random suffix substitutions from Step 1 of Epic 2.

**Type / name consistency:** Resource names follow the naming convention from spec; Terraform module local references are consistent across Epics 2, 4, 9.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-09-aks-deployment.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per Epic (some Epics split into 2-3 subagent runs because they're large), review between, fast iteration. Good for "I want to watch this build."

**2. Inline Execution** — Execute Epic-by-Epic in this session using `superpowers:executing-plans`, batch with manual checkpoints. Good for "I want to drive this myself, one Epic at a time."

User will choose execution mode after the GitHub Issues are created.
