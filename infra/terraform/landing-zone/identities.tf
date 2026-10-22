# CI identities. -plan is read-only and federated to the <env>-plan GitHub
# environment (any branch); -apply changes resources and is federated to
# <env>-apply (main only, and a required reviewer for prod).
resource "azurerm_user_assigned_identity" "plan" {
  name                = "id-${local.name}-plan"
  resource_group_name = azurerm_resource_group.iac.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "apply" {
  name                = "id-${local.name}-apply"
  resource_group_name = azurerm_resource_group.iac.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "plan" {
  name                      = "gh-${var.env}-plan"
  user_assigned_identity_id = azurerm_user_assigned_identity.plan.id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "repo:im-kenough/DineSafeViz:environment:${var.env}-plan"
}

resource "azurerm_federated_identity_credential" "apply" {
  name                      = "gh-${var.env}-apply"
  user_assigned_identity_id = azurerm_user_assigned_identity.apply.id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "repo:im-kenough/DineSafeViz:environment:${var.env}-apply"
}

# Created by hand before Terraform; imported on the first apply.
resource "azuread_group" "operators" {
  display_name     = "sg-${local.name}-operators"
  description      = "Operators of the ${local.name} environment. Managed by Terraform."
  security_enabled = true
  mail_enabled     = false
}

# The operator account is created by hand, because MFA enrollment is
# interactive. Looked up by alias so the tenant domain isn't in the code.
data "azuread_user" "operator" {
  mail_nickname = "dsv-ops-${var.env}01"
}

# Not authoritative: other members (dsv-ops01 until it's deleted) are left
# alone.
resource "azuread_group_member" "operator" {
  group_object_id  = azuread_group.operators.object_id
  member_object_id = data.azuread_user.operator.object_id
}
