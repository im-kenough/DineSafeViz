#!/bin/bash
# Setup az prod and stg environments and provision resources
# (azure-checklist.md steps 1.2 to 4.4)
#
# Usage:
#   ./setup-az-vms.sh infra      # as dsv-admin01: network, identity, vault firewall, roles
#   ./setup-az-vms.sh secrets    # as dsv-ops01: generate the vault secrets
#   SUB_ID=<id> ENV=prod01 ./setup-az-vms.sh infra
#
# The two modes run as different accounts on purpose. dsv-admin01 (Owner) manages
# resources and role assignments but holds no standing data-plane role on the
# vaults; dsv-ops01 reads and writes secrets through its operator group.
set -euo pipefail

#################################
# Account check
#################################
require_account(){
    local upn
    upn=$(az account show --query user.name -o tsv)
    if [[ ${upn%%@*} != "$1" ]]; then
        echo "ERROR: signed in as $upn, but '$MODE' must run as $1" >&2
        exit 1
    fi
}

#################################
# Tags
#################################
create_tags(){
    # $TAGS is deliberately unquoted so each tag becomes its own argument
    for id in $(az group show -n "$RG" --query id -o tsv) \
            $(az keyvault show -n "$KV_NAME" --query id -o tsv); do
        az tag update --resource-id "$id" --operation Merge --tags $TAGS -o none
    done
}

verify_tags(){
    az group list --query "[].{name:name, tags:tags}" -o jsonc
    az resource list --query "[].{name:name, tags:tags}" -o jsonc
}


#################################
# Create Network Security Groups and rules
#################################

create_nsg(){
    echo ""
    # re-creating an existing NSG would reset its rules, so only create it once
    if az network nsg show -g "$RG" -n "$NSG_NAME" -o none 2>/dev/null; then
        echo "NSG $NSG_NAME exists, skipping create"
        return
    fi
    echo "Creating NSG $NSG_NAME..."
    az network nsg create -g "$RG" -n "$NSG_NAME" -l "$LOC" --tags $TAGS -o none
}

configure_nsg_rule(){
    # quoted so '*' reaches az literally instead of globbing to filenames
    echo ""
    echo "Configuring NSG rule $NSG_RULE_NAME..."
    az network nsg rule create -g "$RG" --nsg-name "$NSG_NAME" -n "$NSG_RULE_NAME" \
        --priority "$PRIORITY" --direction "$DIRECTION" --access "$ACCESS" --protocol "$PROTOCOL" \
        --source-address-prefixes "$HOME_IP/$SRC_MASK" --source-port-ranges "$SRC_PORT_RANGES" \
        --destination-address-prefixes "$DST_ADDR_PREFIXES" --destination-port-ranges "$DST_PORT_RANGES" -o none
}

verify_nsg_rule(){
    echo ""
    echo "Verify NSG rule..."
    az network nsg rule list -g "$RG" --nsg-name "$NSG_NAME" -o table
}

#################################
# Create VNET and subnet
#################################
create_vnet(){
    echo ""
    # re-creating an existing VNet would drop the subnet's NSG and service endpoint
    if az network vnet show -g "$RG" -n "$VNET_NAME" -o none 2>/dev/null; then
        echo "VNet $VNET_NAME exists, skipping create"
        return
    fi
    echo "Creating VNet $VNET_NAME..."
    az network vnet create -g "$RG" -n "$VNET_NAME" -l "$LOC" \
        --address-prefixes "$NET.0.0/24" \
        --subnet-name "$SNET_NAME" --subnet-prefixes "$NET.0.0/27" \
        --tags $TAGS -o none
}

#################################
# Attach NSG and the KV and Storage service endpoints to the subnet
#################################
attach_kv_to_nsg_subnet(){
    # the list replaces the subnet's endpoints, so name both
    az network vnet subnet update -g "$RG" --vnet-name "$VNET_NAME" -n "$SNET_NAME" \
        --network-security-group "$NSG_NAME" --service-endpoints Microsoft.KeyVault Microsoft.Storage -o none
}

verify_vnet_service_endpoint(){
    az network vnet subnet show -g "$RG" --vnet-name "$VNET_NAME" -n "$SNET_NAME" \
        --query "{nsg:networkSecurityGroup.id, endpoints:serviceEndpoints[].service}"
}

#################################
# Create the VM's user-assigned managed identity
#################################
create_managed_identity(){
    az identity create -g "$RG" -n "$MI_NAME" -l "$LOC" --tags $TAGS -o none
}

verify_managed_identity() {
    az identity show -g "$RG" -n "$MI_NAME" --query "{client:clientId, principal:principalId}"
}

#################################
# Configure KV Firewall
#################################
get_subnet_id(){
    # functions return values on stdout; 'return' only takes an exit code
    az network vnet subnet show -g "$RG" --vnet-name "$VNET_NAME" \
        -n "$SNET_NAME" --query id -o tsv
}

kv_network_rule_add_by_subnet(){
    az keyvault network-rule add -g "$RG" -n "$KV_NAME" --subnet "$SUBNET_ID" -o none
}

kv_network_rule_add_by_ip(){
    az keyvault network-rule add -g "$RG" -n "$KV_NAME" --ip-address "$KV_NETRULE_IP_ADDR" -o none
}

kv_update_default_deny(){
    # only after both allow rules exist, so you don't lock yourself out
    az keyvault update -g "$RG" -n "$KV_NAME" --default-action Deny --bypass None -o none
}

kv_verify_acl(){
    az keyvault show -n "$KV_NAME" --query properties.networkAcls
}

#################################
# Assign Vault Roles
#################################
get_kv_id(){
    az keyvault show -g "$RG" -n "$KV_NAME" --query id -o tsv
}

get_mi_principal(){
    az identity show -g "$RG" -n "$MI_NAME" --query principalId -o tsv
}

get_group_id(){
    az ad group show --group "$1" --query id -o tsv
}

assign_role(){
    # $1 principal object id, $2 principal type, $3 role name, $4 scope
    # --assignee-principal-type skips the Graph lookup, which can fail for a
    # managed identity that was created seconds ago
    local existing
    existing=$(az role assignment list --scope "$4" \
        --query "[?principalId=='$1' && roleDefinitionName=='$3'] | length(@)" -o tsv)
    if [[ $existing -gt 0 ]]; then
        echo "$3 already assigned to $1, skipping"
        return
    fi
    az role assignment create --assignee-object-id "$1" \
        --assignee-principal-type "$2" \
        --role "$3" --scope "$4" -o none
}

verify_role_assignment(){
    az role assignment list --scope "$KV_ID" --query "[].{who:principalName, type:principalType, role:roleDefinitionName}" -o table
}

#################################
# Storage account for the DineSafe CSVs
#################################
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

create_storage_account(){
    echo ""
    if az storage account show -g "$RG" -n "$ST_NAME" -o none 2>/dev/null; then
        echo "Storage account $ST_NAME exists, skipping create"
        return
    fi
    # names are global across Azure: 3-24 lowercase letters and numbers
    if [[ $(az storage account check-name -n "$ST_NAME" --query nameAvailable -o tsv) != true ]]; then
        echo "ERROR: storage account name $ST_NAME is taken. Pick another (for example ${ST_NAME}a1) and update DSV_STORAGE_ACCOUNT in deploy/$SHORT.env-example" >&2
        exit 1
    fi
    echo "Creating storage account $ST_NAME..."
    # Deny by default from the start; the allow rules follow right after.
    az storage account create -g "$RG" -n "$ST_NAME" -l "$LOC" \
        --sku Standard_LRS --kind StorageV2 --access-tier Hot \
        --allow-shared-key-access false --allow-blob-public-access false \
        --min-tls-version TLS1_2 --https-only true \
        --default-action Deny --bypass None \
        --tags $TAGS -o none
}

configure_storage_protection(){
    # versioning + soft delete are control-plane settings, so the VM's data
    # role can overwrite blobs but can't remove the way back
    az storage account blob-service-properties update -g "$RG" -n "$ST_NAME" \
        --enable-versioning true \
        --enable-delete-retention true --delete-retention-days 7 -o none
    az storage account management-policy create -g "$RG" --account-name "$ST_NAME" \
        --policy @"$SCRIPT_DIR/storage-lifecycle.json" -o none
}

storage_network_rule_add(){
    # same-region traffic ignores IP rules, so the VM needs the subnet rule
    az storage account network-rule add -g "$RG" --account-name "$ST_NAME" \
        --subnet "$SUBNET_ID" -o none
    # a bare address: storage IP rules reject /31 and /32 prefixes
    az storage account network-rule add -g "$RG" --account-name "$ST_NAME" \
        --ip-address "$HOME_IP" -o none
}

create_storage_container(){
    # container-rm goes through Resource Manager, so it needs no data role
    az storage container-rm create -g "$RG" --storage-account "$ST_NAME" \
        -n "$ST_CONTAINER" --public-access off -o none
}

get_container_scope(){
    echo "$(az storage account show -g "$RG" -n "$ST_NAME" --query id -o tsv)/blobServices/default/containers/$ST_CONTAINER"
}

storage_verify(){
    az storage account show -g "$RG" -n "$ST_NAME" --query "{sharedKey:allowSharedKeyAccess, publicBlob:allowBlobPublicAccess, tls:minimumTlsVersion, acls:networkRuleSet}" -o jsonc
    az role assignment list --scope "$CONTAINER_SCOPE" --query "[].{who:principalName, type:principalType, role:roleDefinitionName}" -o table
}

#################################
# Set DSV AZ KV Secrets
#################################
wait_for_secrets_access(){
    # new role assignments and firewall rules can take a few minutes to apply
    local i
    for i in {1..10}; do
        if az keyvault secret list --vault-name "$KV_NAME" -o none 2>/dev/null; then
            return
        fi
        echo "No secrets access on $KV_NAME yet, retrying in 30s ($i/10)..."
        sleep 30
    done
    echo "ERROR: still no secrets access on $KV_NAME. Check the operator group role and the vault firewall (is HOME_IP $HOME_IP?)" >&2
    exit 1
}

set_dsv_az_kv_secrets(){
    echo ""
    echo "Setting DSV secrets in $KV_NAME"
    for name in dsv-db-password dsv-db-migrator-password dsv-db-app-password \
                dsv-analytics-admin-password; do
        # never overwrite: a new value would no longer match the running database
        if az keyvault secret show --vault-name "$KV_NAME" -n "$name" -o none 2>/dev/null; then
            echo "$name exists, skipping (rotate with runbook 9.1 or 9.2)"
            continue
        fi
        az keyvault secret set --vault-name "$KV_NAME" -n "$name" \
            --value "$(openssl rand -hex 32)" -o none
        echo "$name set"
    done
}

verify_az_kv_secret_names(){
    az keyvault secret list --vault-name "$KV_NAME" --query "[].name" -o tsv
}

#################################
# Modes
#################################
run_infra(){
    require_account dsv-admin01

    create_tags
    verify_tags

    NSG_NAME=nsg-dsv-$ENV-app
    NSG_RULE_NAME=AllowSshFromHome
    PRIORITY=100
    DIRECTION=Inbound
    ACCESS=Allow
    PROTOCOL=Tcp
    SRC_MASK=32
    SRC_PORT_RANGES='*'
    DST_ADDR_PREFIXES='*'
    DST_PORT_RANGES=22
    create_nsg
    configure_nsg_rule
    verify_nsg_rule

    # a non overlapping /24 per environment, with a /27 subnet
    # leaving room for later subnets
    SNET_NAME=snet-dsv-$ENV-app
    VNET_NAME=vnet-dsv-$ENV
    create_vnet
    attach_kv_to_nsg_subnet
    verify_vnet_service_endpoint

    MI_NAME=id-dsv-$ENV-vm
    create_managed_identity
    verify_managed_identity

    # Configure KV firewall: allow the VM's subnet (service endpoint) and home IP
    SUBNET_ID=$(get_subnet_id)
    KV_NETRULE_IP_ADDR="$HOME_IP/32"
    kv_network_rule_add_by_subnet
    kv_network_rule_add_by_ip
    kv_update_default_deny
    kv_verify_acl

    # Assign vault roles, scoped to this environment's vault only:
    # the VM identity reads secret values (Secrets User), and the operator
    # group manages them (Secrets Officer). No human user gets a direct role.
    KV_ID=$(get_kv_id)
    MI_PRINCIPAL=$(get_mi_principal)
    assign_role "$MI_PRINCIPAL" ServicePrincipal "Key Vault Secrets User" "$KV_ID"
    # stg operators already hold Secrets Officer on kv-dsv-stg01 (step 1.1)
    if [[ $SHORT == prod ]]; then
        GROUP_ID=$(get_group_id sg-dsv-prod01-operators)
        assign_role "$GROUP_ID" Group "Key Vault Secrets Officer" "$KV_ID"
    fi
    verify_role_assignment

    # Blob Storage for the CSVs: deny by default, allow the VM subnet and
    # home IP; data roles at container scope only
    ST_NAME=stdsv$ENV
    ST_CONTAINER=dinesafe
    create_storage_account
    configure_storage_protection
    storage_network_rule_add
    create_storage_container
    CONTAINER_SCOPE=$(get_container_scope)
    assign_role "$MI_PRINCIPAL" ServicePrincipal "Storage Blob Data Contributor" "$CONTAINER_SCOPE"
    if [[ $SHORT == stg ]]; then
        GROUP_ID=$(get_group_id sg-dsv-stg01-operators)
        assign_role "$GROUP_ID" Group "Storage Blob Data Reader" "$CONTAINER_SCOPE"
    fi
    storage_verify

    echo ""
    echo "Infra done. Next, sign in as dsv-ops01 and run: ENV=$ENV $0 secrets"
}

run_secrets(){
    require_account dsv-ops01

    wait_for_secrets_access
    set_dsv_az_kv_secrets
    verify_az_kv_secret_names

    echo ""
    echo "Secrets done. dsv-tunnel-token is set by hand in checklist step 5.1."
}

main() {
    MODE=${1:-}
    if [[ $MODE != infra && $MODE != secrets ]]; then
        echo "Usage: SUB_ID=<id> [ENV=stg01|prod01] $0 infra|secrets" >&2
        exit 1
    fi

    # common parameters
    ENV=${ENV:-stg01}
    if [[ $ENV != stg01 && $ENV != prod01 ]]; then
        echo "ERROR: ENV must be stg01 or prod01, got '$ENV'" >&2
        exit 1
    fi
    SHORT=${ENV%01}
    RG=rg-dsv-$ENV
    KV_NAME=kv-dsv-$ENV

    #region
    LOC=canadacentral
    TAGS="workload=dsv env=$SHORT owner=dsv-admin01 managed-by=manual"

    # resolves 10.10.0.0 for prod, 10.20.0.0 for stg
    NET=$([ "$SHORT" = prod ] && echo 10.10 || echo 10.20)

    # public IPv4 of home computer for firewall allow listing;
    # Key Vault IP rules are IPv4 only, and a bad value here locks you out
    HOME_IP=$(curl -4 -fsS https://ifconfig.me)
    if [[ ! $HOME_IP =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
        echo "ERROR: unexpected HOME_IP '$HOME_IP'" >&2
        exit 1
    fi
    echo "HOME_IP=$HOME_IP"

    # Subscription by ID: display names can change (sub-dsv-<env>01), and
    # both admin and ops accounts cache subscriptions with the same names.
    SUB_ID=${SUB_ID:?set SUB_ID to the subscription ID of sub-dsv-$ENV}
    az login
    az account set --subscription "$SUB_ID"

    case $MODE in
        infra)   run_infra ;;
        secrets) run_secrets ;;
    esac
}

main "$@"
