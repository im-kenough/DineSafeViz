#!/usr/bin/env bash
# Prints Terraform import blocks for the landing zone resources that existed
# before Terraform: the operator group, its role assignments, and the
# budget. IDs are looked up in Azure at run time so object IDs never reach
# git. `make bootstrap` writes the output to imports.tf (gitignored), and
# `make migrate` deletes it.
#
# Usage: gen-imports.sh stg|prod      (read-only; needs az signed in)
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^(stg|prod)$ ]]; then
    echo "Usage: $0 stg|prod" >&2
    exit 2
fi
env=$1
here=$(cd "$(dirname "$0")" && pwd)
sub=$(sed -n 's/^subscription_id *= *"\(.*\)"/\1/p' "$here/../envs/$env/env.tfvars")
name="dsv-${env}01"
rg="/subscriptions/$sub/resourceGroups/rg-$name"

emit() {
    printf 'import {\n  to = %s\n  id = "%s"\n}\n\n' "$1" "$2"
}

group_id=$(az ad group show --group "sg-$name-operators" --query id -o tsv)
emit azuread_group.operators "/groups/$group_id"

emit azurerm_consumption_budget_subscription.monthly \
    "/subscriptions/$sub/providers/Microsoft.Consumption/budgets/budget-$name-monthly"

# key|role|scope. Keys must match local.role_assignments in rbac.tf. An
# assignment that doesn't exist yet is skipped, and Terraform creates it.
while IFS='|' read -r key role scope; do
    id=$(az role assignment list --subscription "$sub" --assignee "$group_id" \
        --role "$role" --scope "$scope" --query "[?scope=='$scope'].id | [0]" -o tsv)
    if [[ -n $id ]]; then
        emit "azurerm_role_assignment.this[\"$key\"]" "$id"
    fi
done <<EOF
operators-contributor-core|Contributor|$rg
operators-kv-secrets-officer|Key Vault Secrets Officer|$rg/providers/Microsoft.KeyVault/vaults/kv-$name
operators-blob-reader-dinesafe|Storage Blob Data Reader|$rg/providers/Microsoft.Storage/storageAccounts/st${name//-/}/blobServices/default/containers/dinesafe
EOF
