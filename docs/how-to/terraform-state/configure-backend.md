# Configure the Terraform azurerm backend

This guide shows you how to point Terraform at the storage you created in
[Create Azure storage for Terraform state](./create-state-storage.md). The
backend uses Microsoft Entra ID authentication, so you don't need a storage
account key.

## Add the backend block

Backend blocks can't use variables. To keep real values out of git, use a
partial configuration: commit an empty block, and pass the values in at
`terraform init`.

1. In `infra/nx01/backend.tf`, keep only the auth setting:

   ```hcl
   terraform {
     backend "azurerm" {
       use_azuread_auth = true
     }
   }
   ```

2. Copy the example file to a file named for your environment. Git ignores
   `*.backend.hcl`, so the real values stay private.

   ```bash
   cd infra/nx01
   cp stg99.backend.hcl.example stg02.backend.hcl
   ```

3. Fill in `stg02.backend.hcl` with the values from the storage guide:

   ```hcl
   resource_group_name  = "rg-dsv-tf-<env>"        # $RG
   storage_account_name = "<storage-account-name>" # $SA
   container_name       = "tfstate"                # $CONTAINER
   key                  = "<env>.tfstate"
   ```

Each environment has its own storage account and its own `.backend.hcl` file.
The subscription ID comes from `ARM_SUBSCRIPTION_ID`, so it isn't in the file.

## Authenticate

Terraform runs as the service principal, not as your admin user. Set its
credentials as environment variables. Terraform reads them for both the
backend and the `azurerm` provider.

```bash
export ARM_CLIENT_ID="<service-principal-app-id>"   # $SP_APP_ID
ENV="stg02"
export ARM_CLIENT_SECRET="$(cat ~/.az-sp-dsv-tf-${ENV})"
export ARM_TENANT_ID="<tenant-id>"
export ARM_SUBSCRIPTION_ID="<subscription-id>"
```

Read the secret from a file, so it stays out of your shell history. If the file
holds the full `az ad sp create-for-rbac` JSON, use
`jq -r .password ~/.az-sp-dsv-tf-${ENV}` instead of `cat`.

## Initialize

In `infra/nx01`, run `terraform init` with your backend file. If you already
have local state, Terraform asks whether to copy it to the new backend. Answer
`yes`.

```bash
terraform init -migrate-state -backend-config=stg02.backend.hcl
```

Confirm the state file exists:

```bash
az storage blob list --account-name "<storage-account-name>" \
  -c tfstate --auth-mode login -o table
```

<!-- prettier-ignore -->
> [!NOTE]
> A `403` error means the service principal is missing the
> `Storage Blob Data Contributor` role, or the role hasn't applied yet. Wait 5
> minutes, then check the role with `az role assignment list`.

## Next steps

1. Run `terraform plan` to confirm Terraform reads the remote state.
2. Delete the local `terraform.tfstate` and `terraform.tfstate.backup` files.
