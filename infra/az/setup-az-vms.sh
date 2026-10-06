#!/bin/bash
# Setup az prod and stg environments and provision resources
set -euo pipefail

#################################
# Tags
#################################
create_tags(){
    # $TAGS is deliberately unquoted so each tag becomes its own argument
    for id in $(az group show -n "$RG" --query id -o tsv) \
            $(az keyvault show -n "kv-dsv-$ENV" --query id -o tsv); do
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
    echo "Creating NSG $NSG_NAME..."
    az network nsg create -g "$RG" -n "$NSG_NAME" -l "$LOC" --tags $TAGS -o none
}

configure_nsg_rule(){
    # quoted so '*' reaches az literally instead of globbing to filenames
    echo ""
    echo "Configuring NSG rule NSG_NAME..."
    az network nsg rule create -g "$RG" --nsg-name "$NSG_NAME" -n "$NSG_RULE_NAME" \
        --priority "$PRIORITY" --direction "$DIRECTION" --access "$ACCESS" --protocol "$PROTOCOL" \
        --source-address-prefixes "$HOME_IP/$SRC_MASK" --source-port-ranges "$SRC_PORT_RANGES" \
        --destination-address-prefixes "$DST_ADDR_PREFIXES" --destination-port-ranges "$DST_PORT_RANGES" -o none
}

verify_nsg_rule(){
    echo ""
    echo "Verify NSG rule..."
    az network nsg rule list -g $RG --nsg-name nsg-dsv-$ENV-app -o table
}

#################################
# Create VNET and subnet
#################################
create_vnet(){
    az network vnet create -g $RG -n $VNET_NAME -l $LOC \
        --address-prefixes $NET.0.0/24 \
        --subnet-name $SNET_NAME --subnet-prefixes $NET.0.0/24 \
        --tags $TAGS -o none
}

#################################
# Attach KV endpoint to NSG subnet
#################################
attach_kv_to_nsg_subnet(){
    az network vnet subnet update -g $RG --vnet-name $VNET_NAME -n SNET_NAME \
        --network-security-group $NSG_NAME --service-endpoints Microsoft.KeyVault -o none
}

verify_vnet_service_entpoint(){
    az network vnet subnet show -g $RG --vnet-name $VNET_NAME -n SNET_NAME \
        --query "{nsg:networkSecurityGroup.id, endpoints:serviceEndpoints[].service}"
}

#################################
# Attach KV endpoint to NSG subnet
#################################
create_managed_identity(){
    az identity create -g $RG -n $MI_NAME -l $LOC --tags $TAGS -o none
}

verify_managed_identity() {
    az identity show -g $RG -n id-dsv-$ENV-vm --query "{client:clientId, principal:principalId}"
}

#################################
# Configure Firewall
#################################
get_subnet_id(){
    SUBNET_ID=$(az network vnet subnet show -g $RG --vnet-name $VNET_NAME \
        -n $SNET_NAME --query id -o tsv)    
    return "$SUBNET_ID"
}

kv_network_rule_add_by_subnet(){
    az keyvault network-rule add -g $RG -n KV_NETWORK_RULE --subnet "$SUBNET_ID" -o none    
}

kv_network_rule_add_by_ip(){
    az keyvault network-rule add -g $RG -n KV_NETWORK_RULE --ip-address KV_NETRULE_IP_ADDR -o none    
}

kv_update_default_deny(){
    az keyvault update -g $RG -n KV_NAME --default-action Deny --bypass None -o none
}

kv_verify_acl(){
    az keyvault show -n KV_NAME --query properties.networkAcls
}

#################################
# Assign Vault Roles
#################################
get_kv_id(){
    KV_ID=$(az keyvault show -g $RG -n $KV_NAME --query id -o tsv)
    return "$KV_ID"
}

get_mi_principal(){
    MI_PRINCIPAL=$(az identity show -g $RG -n MI_NAME --query principalId -o tsv)
    return "$MI_PRINCIPAL"
}

role_assignment_create(){
    az role assignment create --assignee-object-id "$MI_PRINCIPAL" \
    --assignee-principal-type ServicePrincipal \
    --role "Key Vault Secrets User" --scope "$KV_ID" -o none
}

verify_role_assignment(){
    az role assignment list --scope "$KV_ID" --query "[].{who:principalName, role:roleDefinitionName}" -o table
}

#################################
# Set DSV AZ KV Secrets
#################################
set_dsv_az_kv_secrets(){

    echo ""
    echo "Setting DSV secrets and loading them into $KV_NAME"
    for name in dsv-db-password dsv-db-migrator-password dsv-db-app-password \
                dsv-analytics-admin-password; do
    az keyvault secret set --vault-name $KV_NAME -n "$name" \
        --value "$(openssl rand -hex 32)" -o none
    done
}

verify_az_kv_secret_names(){
    az keyvault secret list --vault-name $KV_NAME --query "[].name" -o tsv
}

main() {
    # common parameters
    # ENV=stg01
    ENV=prod01                                   # prod01 for prod
    SHORT=${ENV%01}                             # stg or prod
    RG=rg-dsv-$ENV

    #region
    LOC=canadacentral
    TAGS="workload=dsv env=$SHORT owner=dsv-admin01 managed-by=manual"
    
    # resolves 10.10.0.0 for prod, 10.20.0.0 for stg
    NET=$([ "$SHORT" = prod ] && echo 10.10 || echo 10.20)

    #returns public IP of home computer for firewall allow listing
    HOME_IP=$(curl -4 -s https://ifconfig.me)
    ADMIN_USER=dsv-vm-admin

    # Authenticate and set your subscription environment
    az login
    az account set --subscription dsv-$ENV
    
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

    # Creating a non overlapping /24 subnet for prod and stg
    # /27 reserved for later subnets
    SNET_NAME=snet-dsv-$ENV-app
    VNET_NAME=vnet-dsv-$ENV
    create_vnet
    attach_kv_to_nsg_subnet
    verify_vnet_service_entpoint

    MI_NAME=id-dsv-$ENV-vm
    create_managed_identity
    verify_managed_identity

    #Configure KV firewall
    SUBNET_ID=$(get_subnet_id)

    # allow VM's subnet, the service endpoint
    KV_NETWORK_RULE=kv-dsv-$ENV
    KV_NETRULE_IP_ADDR="HOME_IP/32"
    KV_NAME=kv-dsv-$ENV
    kv_network_rule_add_by_subnet
    kv_network_rule_add_by_ip
    kv_update_default_deny
    kv_verify_acl

    # Assign Vault roles
    # Assign KV Secrets Officer roles to the Managed Identity for vault access
    KV_ID=$(get_kv_id)
    MI_PRINCIPAL=$(get_mi_principal)
    role_assignment_create
    verify_role_assignment

    #set AZ KV secrets
    set_dsv_az_kv_secrets
    verify_az_kv_secret_names
}

main