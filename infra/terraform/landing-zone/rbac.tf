data "azuread_client_config" "current" {}

locals {
  # Roles the operators and the apply identity may assign in the core
  # resource group: what the VM identity needs, nothing that grants control.
  delegable_role_ids = join(", ", [
    "4633458b-17de-408a-b874-0445c86b69e6", # Key Vault Secrets User
    "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1", # Storage Blob Data Reader
    "ba92f5b4-2d11-453d-a403-e96b0029c9fe", # Storage Blob Data Contributor
  ])

  # Microsoft's "Constrain roles and principal types" condition: write and
  # delete are each allowed only for those roles, and only for service
  # principals (managed identities).
  # https://learn.microsoft.com/azure/role-based-access-control/delegate-role-assignments-examples#example-constrain-roles-and-principal-types
  rbac_admin_condition = trimspace(<<-EOT
    (
     (
      !(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})
     )
     OR
     (
      @Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {${local.delegable_role_ids}}
      AND
      @Request[Microsoft.Authorization/roleAssignments:PrincipalType] ForAnyOfAnyValues:StringEqualsIgnoreCase {'ServicePrincipal'}
     )
    )
    AND
    (
     (
      !(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'})
     )
     OR
     (
      @Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {${local.delegable_role_ids}}
      AND
      @Resource[Microsoft.Authorization/roleAssignments:PrincipalType] ForAnyOfAnyValues:StringEqualsIgnoreCase {'ServicePrincipal'}
     )
    )
  EOT
  )

  kv_id       = "${local.core_rg_id}/providers/Microsoft.KeyVault/vaults/kv-${local.name}"
  dinesafe_id = "${local.core_rg_id}/providers/Microsoft.Storage/storageAccounts/st${local.compact}/blobServices/default/containers/dinesafe"

  principals = {
    operators = { id = azuread_group.operators.object_id, type = "Group" }
    apply     = { id = azurerm_user_assigned_identity.apply.principal_id, type = "ServicePrincipal" }
    plan      = { id = azurerm_user_assigned_identity.plan.principal_id, type = "ServicePrincipal" }
    # Whoever runs the landing zone: dsv-admin01. If the break-glass account
    # ever applies, this assignment moves to it.
    admin = { id = data.azuread_client_config.current.object_id, type = "User" }
  }

  # Keys are stable resource addresses: renaming one destroys and recreates
  # the assignment. Nothing here is scoped to rg-dsv-<env>01-iac except the
  # admin's state access.
  role_assignments = merge(
    {
      operators-contributor-core         = { principal = "operators", role = "Contributor", scope = local.core_rg_id }
      operators-contributor-compute      = { principal = "operators", role = "Contributor", scope = azurerm_resource_group.compute.id }
      operators-rbac-admin-core          = { principal = "operators", role = "Role Based Access Control Administrator", scope = local.core_rg_id, condition = local.rbac_admin_condition }
      operators-kv-secrets-officer       = { principal = "operators", role = "Key Vault Secrets Officer", scope = local.kv_id }
      operators-blob-contributor-tfstate = { principal = "operators", role = "Storage Blob Data Contributor", scope = local.tfstate_container_id }

      apply-contributor-core         = { principal = "apply", role = "Contributor", scope = local.core_rg_id }
      apply-contributor-compute      = { principal = "apply", role = "Contributor", scope = azurerm_resource_group.compute.id }
      apply-rbac-admin-core          = { principal = "apply", role = "Role Based Access Control Administrator", scope = local.core_rg_id, condition = local.rbac_admin_condition }
      apply-blob-contributor-tfstate = { principal = "apply", role = "Storage Blob Data Contributor", scope = local.tfstate_container_id }

      plan-reader-core         = { principal = "plan", role = "Reader", scope = local.core_rg_id }
      plan-reader-compute      = { principal = "plan", role = "Reader", scope = azurerm_resource_group.compute.id }
      plan-blob-reader-tfstate = { principal = "plan", role = "Storage Blob Data Reader", scope = local.tfstate_container_id }

      admin-blob-contributor-landing-zone = { principal = "admin", role = "Storage Blob Data Contributor", scope = local.landing_zone_container_id }
    },
    # Dev loads its local database from stg's raw zone, never prod's.
    var.env == "stg" ? {
      operators-blob-reader-dinesafe = { principal = "operators", role = "Storage Blob Data Reader", scope = local.dinesafe_id }
    } : {}
  )
}

resource "azurerm_role_assignment" "this" {
  for_each = local.role_assignments

  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = local.principals[each.value.principal].id
  principal_type       = local.principals[each.value.principal].type
  condition            = try(each.value.condition, null)
  condition_version    = try(each.value.condition, null) == null ? null : "2.0"
}
