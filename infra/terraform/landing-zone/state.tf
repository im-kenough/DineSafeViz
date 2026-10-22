# State for every layer of this environment. Entra ID only: shared keys are
# off, so every request needs a token and a data role. The public endpoint
# stays on because GitHub-hosted runners have no fixed address; this is a
# documented cost deviation from Microsoft's private endpoint reference.
#trivy:ignore:AVD-AZU-0012
resource "azurerm_storage_account" "tfstate" {
  name                             = "st${local.compact}tfstate"
  resource_group_name              = azurerm_resource_group.iac.name
  location                         = var.location
  account_kind                     = "StorageV2"
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  min_tls_version                  = "TLS1_2"
  https_traffic_only_enabled       = true
  shared_access_key_enabled        = false
  default_to_oauth_authentication  = true
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  local_user_enabled               = false
  sftp_enabled                     = false

  # Versions and soft delete are how you recover a state file that a bad run
  # overwrote or deleted.
  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }
  }

  tags = local.tags

  # Losing this account loses every layer's state.
  lifecycle {
    prevent_destroy = true
  }
}

# core.tfstate and compute.tfstate. Operators and the apply identity write
# here; the plan identity reads.
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"

  lifecycle {
    prevent_destroy = true
  }
}

# landing-zone.tfstate only. Only dsv-admin01 has a role here, so a
# compromised pipeline can't rewrite the state that defines its own access.
resource "azurerm_storage_container" "landing_zone" {
  name                  = "tfstate-landing-zone"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"

  lifecycle {
    prevent_destroy = true
  }
}

# Both IDs are used by rbac.tf.
locals {
  tfstate_container_id      = "${azurerm_storage_account.tfstate.id}/blobServices/default/containers/${azurerm_storage_container.tfstate.name}"
  landing_zone_container_id = "${azurerm_storage_account.tfstate.id}/blobServices/default/containers/${azurerm_storage_container.landing_zone.name}"
}
