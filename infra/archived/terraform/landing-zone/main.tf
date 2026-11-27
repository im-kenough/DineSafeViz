locals {
  name    = "dsv-${var.env}01"
  compact = "dsv${var.env}01"

  tags = {
    workload     = "dsv"
    env          = var.env
    owner        = "dsv-admin01"
    layer        = "landing-zone"
    "managed-by" = "terraform"
  }

  # The core layer's resource group, created by hand and imported by the core
  # layer in sub-project 2. Built from names so this layer doesn't depend on
  # the core layer's state.
  core_rg_id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-${local.name}"
}

resource "azurerm_resource_group" "iac" {
  name     = "rg-${local.name}-iac"
  location = var.location
  tags     = local.tags
}

# Created here so the apply identity never needs to create resource groups,
# which keeps its roles at resource group scope. Empty when the VM is
# destroyed.
resource "azurerm_resource_group" "compute" {
  name     = "rg-${local.name}-compute"
  location = var.location
  tags     = local.tags
}

# Locks are inherited by child resources: while a lock is on, nothing in the
# group can be deleted, including NSG rules, federated credentials, and role
# assignments there. Turn the variable off and apply to delete something.
resource "azurerm_management_lock" "iac" {
  count      = var.lock_iac_rg ? 1 : 0
  name       = "lock-rg-${local.name}-iac"
  scope      = azurerm_resource_group.iac.id
  lock_level = "CanNotDelete"
  notes      = "Landing zone: state and CI identities. Managed by Terraform."
}

resource "azurerm_management_lock" "core" {
  count      = var.lock_core_rg ? 1 : 0
  name       = "lock-rg-${local.name}"
  scope      = local.core_rg_id
  lock_level = "CanNotDelete"
  notes      = "Core layer. Managed by the landing zone."
}

# Created by hand before Terraform; imported on the first apply. Alerts at
# 50, 80, and 100% of actual spend and 100% of forecast spend.
resource "azurerm_consumption_budget_subscription" "monthly" {
  name            = "budget-${local.name}-monthly"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = var.budget_amount
  time_grain      = "Monthly"

  time_period {
    start_date = "2026-10-01T00:00:00Z"
    end_date   = "2036-09-30T00:00:00Z"
  }

  dynamic "notification" {
    for_each = [
      { type = "Actual", threshold = 50 },
      { type = "Actual", threshold = 80 },
      { type = "Actual", threshold = 100 },
      { type = "Forecasted", threshold = 100 },
    ]

    content {
      enabled        = true
      operator       = "GreaterThan"
      threshold      = notification.value.threshold
      threshold_type = notification.value.type
      contact_emails = var.budget_contact_emails
    }
  }
}
