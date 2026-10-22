provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }

  subscription_id = var.subscription_id
  # Shared keys are off on every storage account.
  storage_use_azuread = true
}

# Uses the tenant of your az login.
provider "azuread" {}
