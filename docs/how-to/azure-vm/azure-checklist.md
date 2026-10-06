
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

### Scripts

Steps 1.2 through 4.4 are also scripted in
[`setup-az-vms.sh`](../../../infra/az/setup-az-vms.sh). It runs in two phases,
one per account, so `dsv-admin01` never needs a standing role on the vaults.
Each phase checks the signed-in account and is safe to run again; it doesn't
overwrite existing secrets.

```bash
ENV=stg01 ./infra/az/setup-az-vms.sh infra     # as dsv-admin01
ENV=stg01 ./infra/az/setup-az-vms.sh secrets   # as dsv-ops01
```

To record the current state of both environments, for example after you
finish a part of this checklist, run
[`dump-az-config.sh`](../../../infra/az/dump-az-config.sh) as `dsv-ops01`. It
writes one Markdown file per environment to `az-config/`, with subscription
IDs and IP addresses redacted. It lists secret names but never reads their
values.

```bash
./infra/az/dump-az-config.sh                   # both environments
ENV=prod01 ./infra/az/dump-az-config.sh        # one environment
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
      90-day soft delete. Purge protection is on for both (stg's was turned on
      in step 4.1).
- [x] `rg-dsv-prod01-snapshots`, with no lock.

### 1.2 Done: tag the existing resource groups and vaults

Tags make cost reports and resource searches filterable by workload and
environment. Resources created later in this checklist get tags when they're
created. On October 5, 2026, all four tags were verified on `rg-dsv-stg01`,
`kv-dsv-stg01`, `rg-dsv-prod01`, `kv-dsv-prod01`, and
`rg-dsv-prod01-snapshots`.

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

- **Verify:** Both commands show all four tags on every row. On prod, the
  first command also lists `rg-dsv-prod01-snapshots`.

  ```bash
  az group list --query "[].{name:name, tags:tags}" -o jsonc
  az resource list --query "[].{name:name, tags:tags}" -o jsonc
  ```

- **Source:** [az tag update](https://learn.microsoft.com/cli/azure/tag#az-tag-update)

### 1.3 Role assignments still to do

These assignments need resources that didn't exist when the accounts were set
up. The step that creates each resource assigns its roles.

| Assignment | Scope | Step | Status |
| ---------- | ----- | ---- | ------ |
| `id-dsv-<env>01-vm`: Key Vault Secrets User | `kv-dsv-<env>01` | 4.3 | Done |
| `sg-dsv-prod01-operators`: Key Vault Secrets Officer | `kv-dsv-prod01` | 4.3 | Done |
| `sg-dsv-prod01-operators`: Virtual Machine Contributor | `vm-dsv-prod01` | 6.5 | To do |

## 2. Network

Each environment gets one small VNet with one subnet. The NSG on the subnet
allows SSH from your home IP address only, and the Key Vault service endpoint
lets the VM reach its vault without the vault allowing the VM's public IP.

### 2.1 Done: create the NSG and its SSH rule

The NSG's built-in rules already deny other inbound traffic from the
internet. `AllowSshFromHome` is the only inbound rule; there are no web ports,
because visitors arrive through Cloudflare Tunnel. Verified on both
environments on October 5, 2026.

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

### 2.2 Done: create the VNet and subnet

A `/24` per environment with a `/27` subnet leaves room for later subnets.
The prod and stg ranges don't overlap, so they could be peered later.
Verified on both environments on October 5, 2026. `snet-dsv-prod01-app` was
first created as a `/24` and was resized to `/27` the same day, before
anything was attached to it.

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

### 2.3 Done: attach the NSG and the Key Vault service endpoint to the subnet

The NSG goes on the subnet, not the NIC, so it survives stg VMs being deleted
and recreated. The `Microsoft.KeyVault` service endpoint is free; it lets the
vault firewall allow this subnet by name. Verified on both environments on
October 5, 2026.

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

### 3.1 Done: create `id-dsv-<env>01-vm`

The identity is created empty. Step 4.3 gives it one role on one vault, and
step 6.3 attaches it to the VM as the VM's only identity. Verified on both
environments on October 5, 2026. A stray `id-dsv-prod01-m`, created with a
mistyped name and no role assignments, was deleted the same day.

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

### 4.1 Done: turn on purge protection (stg)

Purge protection stops anyone, including you, from permanently deleting the
vault or its secrets before the 90-day soft-delete period ends. `kv-dsv-prod01`
had it from creation, and it was turned on for `kv-dsv-stg01` on October 5,
2026.

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

### 4.2 Done: restrict the vault firewall

The firewall allows only the VM's subnet, through its service endpoint, and
your home IP address `/32`. Trusted Microsoft services can't bypass it, because
nothing in this design needs them. Add the allow rules before you switch the
default action to **Deny**, so you don't lock yourself out. Verified on both
vaults on October 5, 2026.

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

### 4.3 Done: assign the vault roles

The VM's identity gets **Key Vault Secrets User**, which reads secret values
and nothing else, on its own vault only. For prod, the operator group gets
**Key Vault Secrets Officer** on `kv-dsv-prod01` so that `dsv-ops01` can set
secrets. The stg operator group already has it on `kv-dsv-stg01`. No user
account has a direct role on either vault. Verified on both vaults on October
5, 2026.

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

### 4.4 Done: set the generated secrets

As `dsv-ops01`, from your home network, store four random values. They're
hexadecimal because they end up in `.env` and in a URL, where hex never needs
quoting. The fifth secret, `dsv-tunnel-token`, comes from Cloudflare in step
5.1. A new role assignment can take a few minutes to apply; if you get
`ForbiddenByRbac`, wait and retry. All four names were verified in both vaults
on October 5, 2026.

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


## 5. Cloudflare

Cloudflare provides DNS, TLS, WAF, and DDoS protection, and carries visitor
traffic to the VM through an outbound-only tunnel. Each environment has its
own tunnel and token. The zone settings apply to both hostnames.

### 5.1 Create the tunnel and store its token

The token lets `cloudflared` on the VM connect as this tunnel. It goes
straight into the vault; it isn't stored anywhere else.

- **Dashboard:**
  1. Go to **Networking** > **Tunnels** > **Create a tunnel**. Select
     **Cloudflared**, and name it `tun-dsv-<env>01`.
  2. On the install page, select **Docker**. Copy only the token, which is
     the long string after `--token`. Don't run the command; the VM runs
     `cloudflared` from `docker-compose.vm.yml`.
- **CLI (store the token as `dsv-ops01`):**

  ```bash
  read -rsp "Tunnel token: " TUNNEL_TOKEN; echo
  az keyvault secret set --vault-name kv-dsv-$ENV -n dsv-tunnel-token \
    --value "$TUNNEL_TOKEN" -o none
  unset TUNNEL_TOKEN
  ```

- **Verify:** `az keyvault secret list --vault-name kv-dsv-$ENV --query "[].name" -o tsv`
  now lists five names.
- **Source:** [Create a tunnel (dashboard)](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)

### 5.2 Route the hostname to nginx

The route sends requests for the environment's hostname down the tunnel to
`dsv-nginx` on the VM's Docker network. Cloudflare creates the proxied DNS
record for you.

- **Dashboard:** Open `tun-dsv-<env>01` > **Routes** > **Add route** >
  **Published application**. Choose domain `dinesafeviz.com` and subdomain
  `stg` (leave it empty for prod). Set **Service** to **HTTP** and the URL to
  `dsv-nginx:80`. Select **Add route**. For prod, if the apex already has an
  `A` or `CNAME` record, delete it first.
- **Verify:** **DNS** > **Records** shows a proxied `CNAME` for the hostname
  that points to `<tunnel-id>.cfargotunnel.com`.
- **Source:** [Published applications](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/)

### 5.3 Set the zone's security settings (once)

These settings are zone-wide, so you set them once and they cover both
`dinesafeviz.com` and `stg.dinesafeviz.com`. A per-hostname minimum TLS
version would need the paid Advanced Certificate Manager.

<!-- prettier-ignore -->
> [!WARNING]
> HSTS with **Include subdomains** tells browsers to use HTTPS for every
> subdomain for six months. Don't turn it on until both hostnames work over
> HTTPS.

- **Dashboard:**
  1. **SSL/TLS** > **Edge Certificates**: set **Minimum TLS Version** to
     **TLS 1.3**, and turn on **TLS 1.3**, **Always Use HTTPS**, and
     **Automatic HTTPS Rewrites**.
  2. On the same page, under **HTTP Strict Transport Security (HSTS)**,
     select **Enable HSTS**: **Max Age** 6 months, **Include subdomains** on,
     **Preload** off, **No-Sniff** on.
  3. **Security** > **Settings**: filter by **Bot traffic**, and turn on
     **Bot fight mode**.
  4. In **Security**, open the managed rules and confirm that the
     **Cloudflare Free Managed Ruleset** is enabled.
- **Verify:** `curl -sI https://stg.dinesafeviz.com | grep -i strict-transport`
  shows `max-age=15552000; includeSubDomains`, and
  `curl -s --tls-max 1.2 https://stg.dinesafeviz.com` fails.
- **Source:** [Minimum TLS Version](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/minimum-tls/),
  [HSTS](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/),
  [Bot Fight Mode](https://developers.cloudflare.com/bots/get-started/bot-fight-mode/),
  [Managed rules](https://developers.cloudflare.com/waf/managed-rules/)

## 6. Virtual machines

Each VM runs Ubuntu 24.04 with Docker and nothing else. For stg, steps 6.1
through 6.4 repeat each time you recreate the VM; everything before this part
persists.

### 6.1 Create the public IP address

The public IP gives the VM outbound internet access (Cloudflare, GHCR, apt)
and your SSH path. Standard SKU addresses are billed hourly, even when the
free VM hours apply; check the current price on the
[IP address pricing page](https://azure.microsoft.com/pricing/details/ip-addresses/).

- **Portal:** Go to **Public IP addresses** > **Create**. Select
  `rg-dsv-<env>01`, region **Canada Central**, name `pip-dsv-<env>01`, SKU
  **Standard**, IPv4, assignment **Static**, add the tags, and then select
  **Review + create** > **Create**.
- **CLI:**

  ```bash
  az network public-ip create -g $RG -n pip-dsv-$ENV -l $LOC \
    --sku Standard --allocation-method Static --version IPv4 --tags $TAGS -o none
  ```

- **Source:** [Create a public IP address](https://learn.microsoft.com/azure/virtual-network/ip-services/create-public-ip-portal)

### 6.2 Create the network interface

Creating the NIC separately gives it a CAF name. It has no NSG of its own;
the subnet's NSG applies.

- **Portal:** Go to **Network interfaces** > **Create**. Select
  `rg-dsv-<env>01`, name `nic-dsv-<env>01`, VNet `vnet-dsv-<env>01`, subnet
  `snet-dsv-<env>01-app`, and no NSG. After it's created, open **IP
  configurations** > **ipconfig1**, associate `pip-dsv-<env>01`, and then
  select **Save**.
- **CLI:**

  ```bash
  az network nic create -g $RG -n nic-dsv-$ENV -l $LOC \
    --vnet-name vnet-dsv-$ENV --subnet snet-dsv-$ENV-app \
    --public-ip-address pip-dsv-$ENV --tags $TAGS -o none
  ```

- **Source:** [az network nic create](https://learn.microsoft.com/cli/azure/network/nic#az-network-nic-create)

### 6.3 Create the VM

The VM is a `Standard_B2ats_v2` (2 vCPUs, 1 GiB) with Trusted Launch and a
64 GiB Premium SSD, which the free account's VM and disk allowances cover in
`dsv-prod01`. `id-dsv-<env>01-vm` is its only identity, so IMDS needs no
client ID. For stg, the OS disk and NIC are deleted with the VM; for prod,
they're kept.

- **Portal:** Go to **Virtual machines** > **Create** > **Azure virtual
  machine**.
  1. **Basics:** resource group `rg-dsv-<env>01`, name `vm-dsv-<env>01`, region
     **Canada Central**, no availability zone, security type **Trusted launch
     virtual machines** with **Secure boot** and **vTPM** on, image **Ubuntu
     Server 24.04 LTS - x64 Gen2**, size `Standard_B2ats_v2`, authentication
     **SSH public key** with your admin username and existing public key, and
     **Public inbound ports** **None**.
  2. **Disks:** OS disk size **64 GiB**, type **Premium SSD**; **Delete with
     VM** on for stg, off for prod.
  3. **Networking:** select the existing `nic-dsv-<env>01`, if the portal
     offers it, or VNet `vnet-dsv-<env>01`, subnet `snet-dsv-<env>01-app`,
     public IP `pip-dsv-<env>01`, and NIC network security group **None**.
  4. **Management:** **Identity**: add the user-assigned identity
     `id-dsv-<env>01-vm`, with no system-assigned identity. **Boot
     diagnostics**: **Enable with managed storage account**.
  5. **Tags:** add the tags. Then select **Review + create** > **Create**.
- **CLI:**

  ```bash
  MI_ID=$(az identity show -g $RG -n id-dsv-$ENV-vm --query id -o tsv)
  DELETE_OPTION=$([ "$SHORT" = prod ] && echo Detach || echo Delete)
  az vm create -g $RG -n vm-dsv-$ENV -l $LOC \
    --image Canonical:ubuntu-24_04-lts:server:latest --size Standard_B2ats_v2 \
    --security-type TrustedLaunch --enable-secure-boot true --enable-vtpm true \
    --nics nic-dsv-$ENV --nic-delete-option $DELETE_OPTION \
    --os-disk-name osdisk-dsv-$ENV --os-disk-size-gb 64 --storage-sku Premium_LRS \
    --os-disk-delete-option $DELETE_OPTION \
    --admin-username "$ADMIN_USER" --ssh-key-values ~/.ssh/id_ed25519.pub \
    --assign-identity "$MI_ID" --tags $TAGS -o none
  az vm boot-diagnostics enable -g $RG -n vm-dsv-$ENV -o none
  ```

- **Verify:**

  ```bash
  az vm identity show -g $RG -n vm-dsv-$ENV --query "{type:type, ids:keys(userAssignedIdentities)}"
  az vm show -g $RG -n vm-dsv-$ENV --query "securityProfile.securityType"
  ```

  The identity type is `UserAssigned`, with one ID, and the security type is
  `TrustedLaunch`.
- **Source:** [az vm create](https://learn.microsoft.com/cli/azure/vm#az-vm-create),
  [Delete a VM and attached resources](https://learn.microsoft.com/azure/virtual-machines/delete)

Now harden the OS and install Docker Engine and the Compose plugin, as you
normally would, before step 6.4.

### 6.4 Prepare the serial console

The serial console is your way in if SSH breaks. It needs boot diagnostics
(step 6.3) and a local user with a password. Setting a password doesn't open
SSH password login, as long as `sshd` keeps password authentication off.

- **On the VM:**

  ```bash
  sudo passwd "$USER"        # store it in your password manager, not Key Vault
  sudo sshd -T | grep -Ei '^(passwordauthentication|kbdinteractiveauthentication)'
  echo 'export TMOUT=600' >> ~/.profile   # optional: idle console sessions time out
  ```

  Both `sshd` settings show `no`.
- **Verify:** In the portal, open the VM > **Help** > **Serial console**, and
  sign in with the password.
- **Source:** [Azure Serial Console for Linux](https://learn.microsoft.com/troubleshoot/azure/virtual-machines/linux/serial-console-linux)

### 6.5 Give prod operators VM Contributor (prod)

Prod operators can then start, stop, and use the serial console on
`vm-dsv-prod01`, without being able to change the rest of `rg-dsv-prod01`.

- **Portal:** Open `vm-dsv-prod01` > **Access control (IAM)** > **Add role
  assignment** > **Virtual Machine Contributor** > group
  `sg-dsv-prod01-operators` > **Review + assign**.
- **CLI:**

  ```bash
  VM_ID=$(az vm show -g rg-dsv-prod01 -n vm-dsv-prod01 --query id -o tsv)
  GROUP_ID=$(az ad group show --group sg-dsv-prod01-operators --query id -o tsv)
  az role assignment create --assignee-object-id "$GROUP_ID" --assignee-principal-type Group \
    --role "Virtual Machine Contributor" --scope "$VM_ID" -o none
  ```

- **Source:** [Assign Azure roles using Azure CLI](https://learn.microsoft.com/azure/role-based-access-control/role-assignments-cli)

### 6.6 Add the resource locks

`CanNotDelete` locks stop accidental deletion but still allow changes. Locks
only affect Azure Resource Manager, so secrets and the VM's workload aren't
affected. Prod locks the whole resource group. stg locks only the persistent
pieces, so you can still delete and recreate the VM. The snapshots resource
group has no lock, so old snapshots can be pruned.

- **Portal:** Open the resource group (prod) or each resource (stg) >
  **Settings** > **Locks** > **Add**. Set **Lock type** to **Delete** and use
  the names below.
- **CLI:**

  ```bash
  # prod
  az lock create -n lock-rg-dsv-prod01 --lock-type CanNotDelete -g rg-dsv-prod01 \
    --notes "Prevents accidental deletion of prod" -o none
  # stg: the resources that persist between VMs
  az lock create -n lock-kv-dsv-stg01 --lock-type CanNotDelete -g rg-dsv-stg01 \
    --resource kv-dsv-stg01 --resource-type Microsoft.KeyVault/vaults -o none
  az lock create -n lock-vnet-dsv-stg01 --lock-type CanNotDelete -g rg-dsv-stg01 \
    --resource vnet-dsv-stg01 --resource-type Microsoft.Network/virtualNetworks -o none
  az lock create -n lock-id-dsv-stg01-vm --lock-type CanNotDelete -g rg-dsv-stg01 \
    --resource id-dsv-stg01-vm \
    --resource-type Microsoft.ManagedIdentity/userAssignedIdentities -o none
  ```

- **Verify:** `az lock list -g $RG -o table`
- **Source:** [Lock your Azure resources](https://learn.microsoft.com/azure/azure-resource-manager/management/lock-resources)

## 7. GitHub

The VMs pull public images from GHCR without credentials, and Dependabot and
code scanning report vulnerable dependencies. These are repository settings,
not code.

### 7.1 Done: Dependabot alerts and security updates

Alerts flag dependencies with published advisories; security updates open
PRs that fix them without waiting for the weekly schedule. Both were already
on when checked on October 5, 2026. For public repositories, GitHub keeps
security updates on.

- **Web:** Repository **Settings** > **Advanced Security**: **Dependency
  graph**, **Dependabot alerts**, and **Dependabot security updates** show as
  enabled.
- **Verify:**

  ```bash
  gh api -i repos/im-kenough/DineSafeViz/vulnerability-alerts | head -1   # 204: on
  gh api repos/im-kenough/DineSafeViz/automated-security-fixes            # "enabled":true
  ```

- **Source:** [Configuring Dependabot security updates](https://docs.github.com/code-security/dependabot/dependabot-security-updates/configuring-dependabot-security-updates)

### 7.2 Make the packages public (after the first push to main)

GHCR packages are private when first published. Public packages let the VMs
pull without a token. `images.yml` publishes with `GITHUB_TOKEN`, so the
packages are already linked to the repository.

<!-- prettier-ignore -->
> [!CAUTION]
> A public package can't be made private again.

- **Web:** Your profile > **Packages** > `dsv-app` > **Package settings** >
  **Danger Zone** > **Change visibility** > **Public**. Repeat for
  `dsv-init-db`. Under **Manage Actions access**, confirm that `DineSafeViz`
  is listed.
- **Verify:** `docker logout ghcr.io; docker manifest inspect ghcr.io/im-kenough/dsv-app:main >/dev/null && echo public`
- **Source:** [Configuring a package's access control and visibility](https://docs.github.com/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)

## 8. First deploy

The first deploy proves that every piece fits together. On prod, you also
take the first snapshot and test a restore before the site goes live.

### 8.1 Run the VM setup guide

Follow [Set up an Azure VM for its first deploy](vm-first-time-setup.md),
including the reboot check. It ends with the site serving through the tunnel.

### 8.2 Take a snapshot and prune old ones (prod)

Before every prod deploy, as `dsv-ops01`, take an incremental snapshot of the
OS disk. Incremental snapshots are billed on the changed data only. Keep the
newest three.

```bash
DISK=$(az vm show -g rg-dsv-prod01 -n vm-dsv-prod01 --subscription dsv-prod01 \
  --query storageProfile.osDisk.managedDisk.id -o tsv)
az snapshot create -g rg-dsv-prod01-snapshots --subscription dsv-prod01 \
  -n "snap-dsv-prod01-$(date +%Y%m%d-%H%M)" --source "$DISK" --incremental true -o none
az snapshot list -g rg-dsv-prod01-snapshots --subscription dsv-prod01 \
  --query "sort_by(@, &timeCreated)[:-3].id" -o tsv \
  | xargs -r az snapshot delete --ids
```

- **Source:** [Create an incremental snapshot](https://learn.microsoft.com/azure/virtual-machines/disks-incremental-snapshots)

### 8.3 Test a restore from the snapshot (prod, before go-live)

A snapshot you haven't restored is a hope, not a backup. As `dsv-admin01`,
create a disk from the newest snapshot and swap it in as the OS disk. The
swap needs the same size and Trusted Launch security type.

```bash
SNAP_ID=$(az snapshot list -g rg-dsv-prod01-snapshots \
  --query "sort_by(@, &timeCreated)[-1].id" -o tsv)
az disk create -g rg-dsv-prod01 -n "osdisk-dsv-prod01-$(date +%Y%m%d)" \
  --source "$SNAP_ID" --sku Premium_LRS \
  --hyper-v-generation V2 --security-type TrustedLaunch --tags $TAGS -o none
OLD_DISK=$(az vm show -g rg-dsv-prod01 -n vm-dsv-prod01 \
  --query storageProfile.osDisk.managedDisk.id -o tsv)
az vm deallocate -g rg-dsv-prod01 -n vm-dsv-prod01
az vm update -g rg-dsv-prod01 -n vm-dsv-prod01 \
  --os-disk "$(az disk show -g rg-dsv-prod01 -n "osdisk-dsv-prod01-$(date +%Y%m%d)" --query id -o tsv)"
az vm start -g rg-dsv-prod01 -n vm-dsv-prod01
```

Then SSH in and confirm that `docker compose ps` is healthy and the site
loads. Keep `$OLD_DISK` until you're satisfied. Deleting it needs
`lock-rg-dsv-prod01` removed temporarily; recreate the lock right after.

- **Source:** [Change the OS disk used by an Azure VM](https://learn.microsoft.com/azure/virtual-machines/linux/os-disk-swap)

## 9. Runbooks

These procedures cover changes after the first deploy. Each starts from your
workstation as the account shown, then continues on the VM in
`~/DineSafeViz`.

### 9.1 Rotate a database password

A new vault value doesn't change the running database: `set-passwords.sh` runs
only when the data volume is empty. Change the role's password to the new
value first, then redeploy so the containers pick it up. The app can't open
new database connections between the two steps.

| Secret | Role | `.env` variable |
| ------ | ---- | --------------- |
| `dsv-db-app-password` | `dinesafe_app` | `DSV_DB_APP_PASSWORD` |
| `dsv-db-migrator-password` | `dinesafe_migrator` | `DSV_DB_MIGRATOR_PASSWORD` |
| `dsv-db-password` | `dsv_admin` (the `DSV_DB_USER` superuser) | `DSV_DB_PASSWORD` |

1.  On your workstation, as `dsv-ops01`:

    ```bash
    az keyvault secret set --vault-name kv-dsv-$ENV -n dsv-db-app-password \
      --value "$(openssl rand -hex 32)" -o none
    ```

2.  On the VM, set the role's password from the refreshed `.env`, and then
    redeploy the version that's already running:

    ```bash
    ./scripts/fetch-secrets.sh stg
    ROLE=dinesafe_app VAR=DSV_DB_APP_PASSWORD
    NEW_PW=$(sed -n "s/^$VAR='\(.*\)'$/\1/p" .env)
    echo "ALTER ROLE :\"role\" PASSWORD :'pw';" \
      | docker compose exec -T -e PW="$NEW_PW" -e ROLE="$ROLE" dsv-db \
          sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v role="$ROLE" -v pw="$PW"'
    unset NEW_PW
    ./scripts/deploy.sh stg main      # prod: the running tag, for example v0.5.0
    ```

### 9.2 Rotate the Grafana admin password

Grafana creates its admin user on first start only, so a new
`GF_SECURITY_ADMIN_PASSWORD` alone doesn't change it. Reset it with the
Grafana CLI, then redeploy so `dsv-init-analytics` uses the new value.

1.  On your workstation, as `dsv-ops01`:

    ```bash
    az keyvault secret set --vault-name kv-dsv-$ENV -n dsv-analytics-admin-password \
      --value "$(openssl rand -hex 32)" -o none
    ```

2.  On the VM:

    ```bash
    ./scripts/fetch-secrets.sh stg
    sed -n "s/^DSV_ANALYTICS_ADMIN_PASSWORD='\(.*\)'$/\1/p" .env \
      | docker compose exec -T dsv-analytics grafana cli admin reset-admin-password --password-from-stdin
    ./scripts/deploy.sh stg main
    ```

### 9.3 Rotate the tunnel token

Refreshing the token stops the old one from opening new connections; the
running connector stays up until the redeploy restarts it.

1.  In the Cloudflare dashboard, go to **Networking** > **Tunnels** >
    `tun-dsv-<env>01` > **Overview** > **Refresh token**, and copy the new
    token from the install command.
2.  Store it as in step 5.1.
3.  On the VM, run `./scripts/deploy.sh stg main` (prod: the running tag).

### 9.4 Recover a deleted vault or secret

Purge protection means deleted vaults and secrets stay recoverable for 90
days, and their names stay reserved.

- **Vault**, as `dsv-admin01`: `az keyvault recover -n kv-dsv-$ENV`. Recovery
  doesn't restore role assignments, so repeat step 4.3, then check step 4.2's
  firewall rules.
- **Secret**, as `dsv-ops01`:
  `az keyvault secret recover --vault-name kv-dsv-$ENV -n <secret-name>`, then
  set a new version as in step 4.4 if the old value is no longer wanted.

### 9.5 Delete and recreate the stg VM

stg only needs to exist while you're testing. Deleting the VM also deletes
its OS disk and NIC (step 6.3's delete options); the identity, vault, VNet,
NSG, and tunnel stay. While the VM is gone, `stg.dinesafeviz.com` shows a
Cloudflare error.

```bash
az vm delete -g rg-dsv-stg01 -n vm-dsv-stg01 --yes
az network public-ip delete -g rg-dsv-stg01 -n pip-dsv-stg01
```

To recreate it, repeat steps 6.1 through 6.4 for stg, then step 8.1. The
first time you do this, confirm that the VNet lock doesn't block the NIC
deletion, and note the result in this checklist.

## Next steps

- Deploy changes as described in [CI and CD](../../explanation/azure-vm/ci-cd.md).
- If SSH or Key Vault access stops working, see
  [Troubleshoot: your home IP address changed](troubleshoot-home-ip-change.md).
