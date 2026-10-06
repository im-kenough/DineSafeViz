# Troubleshoot: your home IP address changed

This guide explains how to restore access to the Azure VMs, key vaults, and
storage accounts when your home public IP address changes. It lists the symptoms, which account to
use for each environment, and the portal and Azure CLI steps.

<!-- prettier-ignore -->
> [!NOTE]
> This describes the target state for the Azure VM deployment. Resource names
> match the Azure checklist and
> [Identity and access management](../../ref/iam.md).

## Symptoms

Three firewall rules trust your home IP address. When it changes, they stop
matching, and you see these errors:

- **SSH to the VM times out.** The NSG rule `AllowSshFromHome` on
  `nsg-dsv-<env>01-app` only allows port 22 from your old address.
- **Key Vault returns `403 Forbidden` with `ForbiddenByFirewall`.** The vault
  firewall only allows your old address. In the portal, you can open the vault
  but can't list its secrets.
- **`scripts/data.sh dev` fails with HTTP 403 (`AuthorizationFailure`).**
  The storage account firewall on `stdsv<env>01` only allows your old address.

The site itself isn't affected. Visitors reach it through Cloudflare Tunnel,
and the VM reaches Key Vault and Blob Storage through its subnet's service
endpoints, so none of them depend on your IP address.

## Why you can always fix it remotely

These rules filter traffic to the VM and to the vault's and storage
account's data planes only. Changing
the rules goes through Azure Resource Manager, which isn't restricted by your
IP address. You can update them from any network, as long as your account has
the right role.

## Which account to use

The account you need depends on the environment, because prod operators can't
change prod infrastructure.

| Environment | Account       | Role that allows the change                        |
| ----------- | ------------- | -------------------------------------------------- |
| stg         | `dsv-ops01`   | Contributor on `rg-dsv-stg01`, through `sg-dsv-stg01-operators` |
| prod        | `dsv-admin01` | Owner at the Tenant Root Group                     |

`dsv-ops01` has only Reader on `rg-dsv-prod01`, so it can't edit the prod NSG
or firewalls. Sign in as `dsv-admin01` for prod, make only these changes,
then sign out.

## Update the rules

Update every rule for each environment you use, then remove your old address.

1.  Find your current public IPv4 address. Key Vault firewall rules support
    IPv4 only, so force IPv4:

    ```bash
    curl -4 -s https://ifconfig.me; echo
    ```

2.  Sign in with the account for the environment, and set the variables. This
    example uses stg. For prod, use `dsv-admin01`, `ENV=prod01`, and the ID
    of subscription `sub-dsv-prod01`. Set `SUB_ID` to the subscription ID,
    which `az account list -o table` shows.

    ```bash
    az login        # dsv-ops01 for stg, dsv-admin01 for prod
    ENV=stg01
    SUB_ID=<subscription-id>
    az account set --subscription "$SUB_ID"
    NEW_IP=$(curl -4 -s https://ifconfig.me)
    ```

3.  Update the NSG rule so SSH accepts your new address.

    - **Portal:** Go to **Network security groups** > **nsg-dsv-stg01-app** >
      **Inbound security rules** > **AllowSshFromHome**. Set **Source IP
      addresses/CIDR ranges** to your new address, and then select **Save**.
    - **CLI:**

      ```bash
      az network nsg rule update -g rg-dsv-$ENV --nsg-name nsg-dsv-$ENV-app \
        -n AllowSshFromHome --source-address-prefixes "$NEW_IP/32"
      ```

4.  Add your new address to the vault firewall, and remove the old one.

    - **Portal:** Go to **Key vaults** > **kv-dsv-stg01** > **Networking** >
      **Firewalls and virtual networks**. Under **Firewall**, add your new
      address, delete the old one, and then select **Save**.
    - **CLI:**

      ```bash
      az keyvault network-rule list -g rg-dsv-$ENV -n kv-dsv-$ENV --query ipRules -o tsv
      az keyvault network-rule add -g rg-dsv-$ENV -n kv-dsv-$ENV --ip-address "$NEW_IP/32"
      az keyvault network-rule remove -g rg-dsv-$ENV -n kv-dsv-$ENV --ip-address "<old-ip>/32"
      ```

5.  Add your new address to the storage account firewall, and remove the
    old one. Storage IP rules take a bare address, not a `/32` range.

    - **Portal:** Go to **Storage accounts** > **stdsvstg01** >
      **Networking**. Under **Firewall**, add your new address, delete the
      old one, and then select **Save**.
    - **CLI:**

      ```bash
      az storage account network-rule list -g rg-dsv-$ENV --account-name stdsv$ENV --query ipRules -o tsv
      az storage account network-rule add -g rg-dsv-$ENV --account-name stdsv$ENV --ip-address "$NEW_IP"
      az storage account network-rule remove -g rg-dsv-$ENV --account-name stdsv$ENV --ip-address "<old-ip>"
      ```

6.  Verify each path:

    ```bash
    az keyvault secret list --vault-name kv-dsv-$ENV --query "[].name" -o tsv
    ssh <admin-user>@<vm-public-ip> true && echo "SSH OK"
    scripts/data.sh dev        # stg only: syncs the CSVs into ./data
    ```

Rule changes can take a few minutes to apply. If verification fails right away,
wait and try again.

## If you can't sign in to Azure

If you can't sign in, for example because MFA fails, the IP address isn't the
problem. Use the break-glass account to regain access, then fix the original
account. Don't use the break-glass account for routine rule updates.

## Related documents

- [Identity and access management](../../ref/iam.md): accounts, groups,
  and role assignments.
- [Configure network security for Azure Key Vault](https://learn.microsoft.com/azure/key-vault/general/network-security#firewall-settings):
  firewall rule limits and CLI reference.
- [Create an IP network rule for Azure Storage](https://learn.microsoft.com/azure/storage/common/storage-network-security-ip-address-range):
  storage firewall CLI reference.
