data "azurerm_client_config" "current" {}

# Sub-project 4 stores these as GitHub environment variables. Client IDs
# aren't secrets, but they aren't committed either.
output "plan_client_id" {
  description = "Client ID of id-dsv-<env>01-plan, for the <env>-plan GitHub environment."
  value       = azurerm_user_assigned_identity.plan.client_id
}

output "apply_client_id" {
  description = "Client ID of id-dsv-<env>01-apply, for the <env>-apply GitHub environment."
  value       = azurerm_user_assigned_identity.apply.client_id
}

output "tenant_id" {
  description = "Entra tenant ID."
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "The environment's subscription ID."
  value       = var.subscription_id
}

output "state_account_name" {
  description = "Storage account that holds every layer's state."
  value       = azurerm_storage_account.tfstate.name
}
