
# Azure checklist for the stg and prod VMs

This checklist creates and configures the Azure, Cloudflare, and GitHub
resources that the DineSafeViz VMs need. Each step explains what it does and
why, then gives the portal steps and the equivalent Azure CLI commands. Work
through the parts in order, once for stg and once for prod.

<!-- prettier-ignore -->
> [!NOTE]
> Steps marked **Done** were applied on October 5, 2026. The rest describe the
> target state. Validate each step the first time you run it, and update this
> checklist with what you find.

## Before you begin

Run each step as `dsv-admin01` unless the step names another account.
`dsv-admin01` holds Owner at the Tenant Root Group, which covers role
assignments and locks. Key Vault's RBAC model keeps secrets separate, so
reading and writing secrets uses `dsv-ops01`, through the operator groups.

| Work | Account | Why |
| ---- | ------- | --- |
| Role assignments, locks, all prod infrastructure | `dsv-admin01` | Needs Owner; prod operators only have Reader on `rg-dsv-prod01` |
| Other stg infrastructure | `dsv-ops01` or `dsv-admin01` | stg operators have Contributor on `rg-dsv-stg01` |
| Set or read secrets | `dsv-ops01` | Needs Key Vault Secrets Officer on the vault |
| Prod snapshots | `dsv-ops01` | Disk Snapshot Contributor on `rg-dsv-prod01-snapshots` |

Set these variables once per shell. They're used by every CLI step. `TAGS` is
deliberately unquoted where it's used, so each tag becomes its own argument.

```bash
az login
ENV=stg01                                   # prod01 for prod
SHORT=${ENV%01}                             # stg or prod
RG=rg-dsv-$ENV
LOC=canadacentral
TAGS="workload=dsv env=$SHORT owner=dsv-admin01 managed-by=manual"
NET=$([ "$SHORT" = prod ] && echo 10.10 || echo 10.20)
HOME_IP=$(curl -4 -s https://ifconfig.me)   # Key Vault rules are IPv4 only
ADMIN_USER=<your-vm-admin-username>
az account set --subscription dsv-$ENV
```

## 1. Entra ID and RBAC

Accounts, groups, and the role assignments that don't depend on new resources
are already in place. The full inventory is in
[Identity and access management](../../ref/iam.md).

### 1.1 Done: accounts, groups, budgets, vaults, and snapshot resource group

The following items exist and were verified on October 5, 2026.

- [x] `dsv-admin01`, `dsv-ops01`, and the break-glass account, with MFA through
      security defaults.
- [x] `sg-dsv-prod01-operators`: Reader on `rg-dsv-prod01`, Disk Snapshot
      Contributor on `rg-dsv-prod01-snapshots`.
- [x] `sg-dsv-stg01-operators`: Contributor on `rg-dsv-stg01`, Key Vault Secrets
      Officer on `kv-dsv-stg01`.
- [x] `budget-dsv-prod01-monthly` and `budget-dsv-stg01-monthly`: 40 CAD, alerts
      at 50, 80, and 100% actual and 100% forecast.
- [x] `kv-dsv-prod01` and `kv-dsv-stg01`: Standard, RBAC permission model,
      90-day soft delete. Purge protection is on for prod only (see 4.1).
- [x] `rg-dsv-prod01-snapshots`, with no lock.

### 1.2 Tag the existing resource groups and vaults

Tags make cost reports and resource searches filterable by workload and
environment. Resources created later in this checklist get tags when they're
created.

- **Portal:** For each of `rg-dsv-<env>01`, `kv-dsv-<env>01`, and (prod only)
  `rg-dsv-prod01-snapshots`, open the resource, select **Tags**, add
  `workload=dsv`, `env=<stg|prod>`, `owner=dsv-admin01`, and
  `managed-by=manual`, and then select **Apply**.
- **CLI:**

  ```bash
  for id in $(az group show -n $RG --query id -o tsv) \
            $(az keyvault show -n kv-dsv-$ENV --query id -o tsv); do
    az tag update --resource-id "$id" --operation Merge --tags $TAGS -o none
  done
  # prod only:
  az tag update --operation Merge --tags $TAGS -o none \
    --resource-id "$(az group show -n rg-dsv-prod01-snapshots --query id -o tsv)"
  ```

- **Verify:** `az group show -n $RG --query tags`
- **Source:** [az tag update](https://learn.microsoft.com/cli/azure/tag#az-tag-update)

### 1.3 Role assignments still to do

These assignments need resources that don't exist yet. The step that creates
each resource assigns its roles.

| Assignment | Scope | Step |
| ---------- | ----- | ---- |
| `id-dsv-<env>01-vm`: Key Vault Secrets User | `kv-dsv-<env>01` | 4.3 |
| `sg-dsv-prod01-operators`: Key Vault Secrets Officer | `kv-dsv-prod01` | 4.3 |
| `sg-dsv-prod01-operators`: Virtual Machine Contributor | `vm-dsv-prod01` | 6.5 |

## 2. Network

Each environment gets one small VNet with one subnet. The NSG on the subnet
allows SSH from your home IP address only, and the Key Vault service endpoint
lets the VM reach its vault without the vault allowing the VM's public IP.

### 2.1 Create the NSG and its SSH rule

The NSG's built-in rules already deny other inbound traffic from the
internet. `AllowSshFromHome` is the only inbound rule; there are no web ports,
because visitors arrive through Cloudflare Tunnel.

- **Portal:**
  1. Go to **Network security groups** > **Create**. Select resource group
     `rg-dsv-<env>01`, name `nsg-dsv-<env>01-app`, region **Canada Central**,
     add the tags, and then select **Review + create** > **Create**.
  2. Open the NSG and go to **Settings** > **Inbound security rules** >
     **Add**. Set **Source** to **IP Addresses** with your home IP address
     followed by `/32`, **Service** to **SSH**, **Action** to **Allow**,
     **Priority** to `100`, and **Name** to `AllowSshFromHome`. Select **Add**.
- **CLI:**

  ```bash
  az network nsg create -g $RG -n nsg-dsv-$ENV-app -l $LOC --tags $TAGS -o none
  az network nsg rule create -g $RG --nsg-name nsg-dsv-$ENV-app -n AllowSshFromHome \
    --priority 100 --direction Inbound --access Allow --protocol Tcp \
    --source-address-prefixes "$HOME_IP/32" --source-port-ranges '*' \
    --destination-address-prefixes '*' --destination-port-ranges 22 -o none
  ```

- **Verify:** `az network nsg rule list -g $RG --nsg-name nsg-dsv-$ENV-app -o table`
  shows one rule.
- **Source:** [Create, change, or delete a network security group](https://learn.microsoft.com/azure/virtual-network/manage-network-security-group)

### 2.2 Create the VNet and subnet

A `/24` per environment with a `/27` subnet leaves room for later subnets.
The prod and stg ranges don't overlap, so they could be peered later.

- **Portal:** Go to **Virtual networks** > **Create**. Select
  `rg-dsv-<env>01`, name `vnet-dsv-<env>01`, region **Canada Central**. On
  **IP addresses**, set the address space to `10.10.0.0/24` (prod) or
  `10.20.0.0/24` (stg), delete the default subnet, and add
  `snet-dsv-<env>01-app` with the first `/27` of that range. Add the tags,
  and then select **Review + create** > **Create**.
- **CLI:**

  ```bash
  az network vnet create -g $RG -n vnet-dsv-$ENV -l $LOC \
    --address-prefixes $NET.0.0/24 \
    --subnet-name snet-dsv-$ENV-app --subnet-prefixes $NET.0.0/27 \
    --tags $TAGS -o none
  ```

- **Source:** [az network vnet create](https://learn.microsoft.com/cli/azure/network/vnet#az-network-vnet-create)

### 2.3 Attach the NSG and the Key Vault service endpoint to the subnet

The NSG goes on the subnet, not the NIC, so it survives stg VMs being deleted
and recreated. The `Microsoft.KeyVault` service endpoint is free; it lets the
vault firewall allow this subnet by name.

- **Portal:** Open `vnet-dsv-<env>01` > **Subnets** > `snet-dsv-<env>01-app`.
  Set **Network security group** to `nsg-dsv-<env>01-app`, and under
  **Service endpoints** add `Microsoft.KeyVault`. Select **Save**.
- **CLI:**

  ```bash
  az network vnet subnet update -g $RG --vnet-name vnet-dsv-$ENV -n snet-dsv-$ENV-app \
    --network-security-group nsg-dsv-$ENV-app --service-endpoints Microsoft.KeyVault -o none
  ```

- **Verify:**

  ```bash
  az network vnet subnet show -g $RG --vnet-name vnet-dsv-$ENV -n snet-dsv-$ENV-app \
    --query "{nsg:networkSecurityGroup.id, endpoints:serviceEndpoints[].service}"
  ```

- **Source:** [Virtual network service endpoints](https://learn.microsoft.com/azure/virtual-network/virtual-network-service-endpoints-overview)

## 3. Managed identity

The VM signs in to Key Vault as a user-assigned managed identity. Unlike a
system-assigned identity, it outlives the VM, so recreating the stg VM doesn't
require new role assignments.

### 3.1 Create `id-dsv-<env>01-vm`

The identity is created empty. Step 4.3 gives it one role on one vault, and
step 6.3 attaches it to the VM as the VM's only identity.

- **Portal:** Go to **Managed Identities** > **Create**. Select
  `rg-dsv-<env>01`, region **Canada Central**, name `id-dsv-<env>01-vm`, add
  the tags, and then select **Review + create** > **Create**.
- **CLI:**

  ```bash
  az identity create -g $RG -n id-dsv-$ENV-vm -l $LOC --tags $TAGS -o none
  ```

- **Verify:** `az identity show -g $RG -n id-dsv-$ENV-vm --query "{client:clientId, principal:principalId}"`
- **Source:** [Manage user-assigned managed identities](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/how-manage-user-assigned-managed-identities)

## 4. Key vaults

Each environment's vault holds that environment's five secrets. The vault
uses RBAC, so Owner and Contributor don't grant access to secrets, and a
firewall allows only the VM's subnet and your home IP address.

### 4.1 Turn on purge protection (stg)

Purge protection stops anyone, including you, from permanently deleting the
vault or its secrets before the 90-day soft-delete period ends. `kv-dsv-prod01`
already has it. `kv-dsv-stg01` doesn't.

<!-- prettier-ignore -->
> [!CAUTION]
> Purge protection can't be turned off. After this step, a deleted
> `kv-dsv-stg01` keeps its name reserved for 90 days. Confirm that you want
> this before you run the step.

- **Portal:** Open `kv-dsv-stg01` > **Settings** > **Properties**. Under
  **Purge protection**, select **Enable purge protection**, and then select
  **Save**.
- **CLI:**

  ```bash
  az keyvault update -g rg-dsv-stg01 -n kv-dsv-stg01 --enable-purge-protection true -o none
  ```

- **Verify:** `az keyvault show -n kv-dsv-$ENV --query properties.enablePurgeProtection`
  returns `true` for both vaults.
- **Source:** [Azure Key Vault soft-delete overview](https://learn.microsoft.com/azure/key-vault/general/soft-delete-overview)

### 4.2 Restrict the vault firewall

The firewall allows only the VM's subnet, through its service endpoint, and
your home IP address `/32`. Trusted Microsoft services can't bypass it, because
nothing in this design needs them. Add the allow rules before you switch the
default action to **Deny**, so you don't lock yourself out.

- **Portal:** Open the vault > **Settings** > **Networking** > **Firewalls and
  virtual networks**. Select **Allow public access from specific virtual
  networks and IP addresses**. Select **Add a virtual network** > **Add
  existing virtual networks**, and choose `vnet-dsv-<env>01` /
  `snet-dsv-<env>01-app`. Under **Firewall**, add your home IP address. Clear
  **Allow trusted Microsoft services to bypass this firewall**, and then
  select **Apply**.
- **CLI:**

  ```bash
  SUBNET_ID=$(az network vnet subnet show -g $RG --vnet-name vnet-dsv-$ENV \
    -n snet-dsv-$ENV-app --query id -o tsv)
  az keyvault network-rule add -g $RG -n kv-dsv-$ENV --subnet "$SUBNET_ID" -o none
  az keyvault network-rule add -g $RG -n kv-dsv-$ENV --ip-address "$HOME_IP/32" -o none
  az keyvault update -g $RG -n kv-dsv-$ENV --default-action Deny --bypass None -o none
  ```

- **Verify:**

  ```bash
  az keyvault show -n kv-dsv-$ENV --query properties.networkAcls
  ```

  `defaultAction` is `Deny`, `bypass` is `None`, and there's one IP rule and
  one virtual network rule. If your home IP address changes later, see
  [Troubleshoot: your home IP address changed](troubleshoot-home-ip-change.md).
- **Source:** [Configure network security for Azure Key Vault](https://learn.microsoft.com/azure/key-vault/general/network-security)

### 4.3 Assign the vault roles

The VM's identity gets **Key Vault Secrets User**, which reads secret values
and nothing else, on its own vault only. For prod, the operator group gets
**Key Vault Secrets Officer** on `kv-dsv-prod01` so that `dsv-ops01` can set
secrets. The stg operator group already has it on `kv-dsv-stg01`.

- **Portal:** Open the vault > **Access control (IAM)** > **Add** > **Add role
  assignment**. Select **Key Vault Secrets User**, then **Managed identity**
  > **Select members** > **User-assigned managed identity** >
  `id-dsv-<env>01-vm`. Select **Review + assign**. For prod, repeat with
  **Key Vault Secrets Officer** and the group `sg-dsv-prod01-operators`.
- **CLI:**

  ```bash
  KV_ID=$(az keyvault show -g $RG -n kv-dsv-$ENV --query id -o tsv)
  MI_PRINCIPAL=$(az identity show -g $RG -n id-dsv-$ENV-vm --query principalId -o tsv)
  az role assignment create --assignee-object-id "$MI_PRINCIPAL" \
    --assignee-principal-type ServicePrincipal \
    --role "Key Vault Secrets User" --scope "$KV_ID" -o none
  # prod only:
  GROUP_ID=$(az ad group show --group sg-dsv-prod01-operators --query id -o tsv)
  az role assignment create --assignee-object-id "$GROUP_ID" \
    --assignee-principal-type Group \
    --role "Key Vault Secrets Officer" --scope "$KV_ID" -o none
  ```

- **Verify:** `az role assignment list --scope "$KV_ID" --query "[].{who:principalName, role:roleDefinitionName}" -o table`
- **Source:** [Azure built-in roles for Key Vault data plane operations](https://learn.microsoft.com/azure/key-vault/general/rbac-guide)

### 4.4 Set the generated secrets

As `dsv-ops01`, from your home network, store four random values. They're
hexadecimal because they end up in `.env` and in a URL, where hex never needs
quoting. The fifth secret, `dsv-tunnel-token`, comes from Cloudflare in step
5.1. A new role assignment can take a few minutes to apply; if you get
`ForbiddenByRbac`, wait and retry.

- **Portal:** Open the vault > **Objects** > **Secrets** > **Generate/Import**.
  For each name below, paste the output of `openssl rand -hex 32` as the value,
  and then select **Create**.
- **CLI:**

  ```bash
  for name in dsv-db-password dsv-db-migrator-password dsv-db-app-password \
              dsv-analytics-admin-password; do
    az keyvault secret set --vault-name kv-dsv-$ENV -n "$name" \
      --value "$(openssl rand -hex 32)" -o none
  done
  ```

- **Verify:** `az keyvault secret list --vault-name kv-dsv-$ENV --query "[].name" -o tsv`
  lists the four names.
- **Source:** [az keyvault secret set](https://learn.microsoft.com/cli/azure/keyvault/secret#az-keyvault-secret-set)
