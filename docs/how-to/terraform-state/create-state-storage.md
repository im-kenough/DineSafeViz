# Create Azure storage for Terraform state

This guide shows you how to create a separate Azure storage account that holds
Terraform state files. Keep it apart from the resources Terraform manages, so
a `terraform destroy` can't delete its own state.

## Before you begin

You run every step in this guide as an admin user, not as the Terraform
service principal. The service principal can't assign roles, so it can't set
up its own access.

You need:

- The Azure CLI.
- An admin user with Owner, or Contributor plus User Access Administrator, on
  the subscription.
- The app ID of the Terraform service principal.

Sign in as the admin user and confirm the account:

```bash
az login
az account show --query user -o table
```

The output must show your admin user, not the service principal app ID.

## Set variables

Set these values once in your terminal. The storage account name must be
globally unique, 3 to 24 characters, lowercase letters and numbers only. The
suffix comes from `openssl rand -hex 4`, which uses a cryptographically secure
random source and returns 8 characters (`0-9` and `a-f`).

```bash
ENV="stg02"
SUB_ID="<subscription-id>"
LOCATION="canadacentral"
RG="rg-dsv-tf-${ENV}"
SA="stdsvtf${ENV}$(openssl rand -hex 4)"   # 12 + 8 = 20 characters, no dashes
CONTAINER="tfstate"
SP_APP_ID="<service-principal-app-id>"
echo "$SA"   # note this name, you need it in the backend config
```

## Create the storage

Create the resource group, the storage account, and its settings.

1. Create the resource group:

   ```bash
   az group create --subscription "$SUB_ID" -n "$RG" -l "$LOCATION"
   ```

2. Create the storage account. This turns off public blob access and shared
   keys, and requires TLS 1.2:

   ```bash
   az storage account create --subscription "$SUB_ID" -g "$RG" -n "$SA" \
     -l "$LOCATION" --sku Standard_LRS --kind StorageV2 \
     --allow-blob-public-access false \
     --allow-shared-key-access false \
     --min-tls-version TLS1_2
   ```

3. Turn on versioning and soft delete, so you can recover an older state file:

   ```bash
   az storage account blob-service-properties update --subscription "$SUB_ID" \
     -g "$RG" --account-name "$SA" \
     --enable-versioning true \
     --enable-delete-retention true --delete-retention-days 14
   ```

## Assign permissions

Shared keys are off, so every identity that reads or writes blobs needs a data
role. Owner and Contributor don't include data access.

1. Look up the IDs you need:

   ```bash
   SA_ID=$(az storage account show --subscription "$SUB_ID" -g "$RG" -n "$SA" \
     --query id -o tsv)
   ME=$(az ad signed-in-user show --query id -o tsv)
   SP_OBJECT_ID=$(az ad sp show --id "$SP_APP_ID" --query id -o tsv)
   echo "$SA_ID" "$ME" "$SP_OBJECT_ID"   # all three must be non-empty
   ```

2. Give your admin user data access, so you can create the container:

   ```bash
   az role assignment create --assignee-object-id "$ME" \
     --assignee-principal-type User \
     --role "Storage Blob Data Contributor" --scope "$SA_ID"
   ```

3. Give the Terraform service principal data access:

   ```bash
   az role assignment create --assignee-object-id "$SP_OBJECT_ID" \
     --assignee-principal-type ServicePrincipal \
     --role "Storage Blob Data Contributor" --scope "$SA_ID"
   ```

4. Confirm both assignments:

   ```bash
   az role assignment list --scope "$SA_ID" -o table
   ```

New role assignments can take up to 5 minutes to apply. If the next step fails
with an authorization error, wait and try again.

## Create the container

Create the blob container that holds the state files:

```bash
az storage container create --account-name "$SA" -n "$CONTAINER" \
  --auth-mode login
```

The output `"created": true` means it worked.

Optional: Lock the resource group so nobody deletes it by accident:

```bash
az lock create --name lock-tfstate --lock-type CanNotDelete \
  --resource-group "$RG" --subscription "$SUB_ID"
```

## Verify

List the container to confirm access works:

```bash
az storage blob list --account-name "$SA" -c "$CONTAINER" --auth-mode login
```

An empty list (`[]`) means it works.

<!-- prettier-ignore -->
> [!IMPORTANT]
> State files can contain secrets in plain text. Grant the data role only to
> the identities that need it.

## Next steps

Connect Terraform to the new storage with
[Configure the Terraform azurerm backend](./configure-backend.md).
