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
    az network nsg create -g "$RG" -n "$NSG_NAME" -l "$LOC" --tags $TAGS -o none
}

configure_nsg_rule(){
    # quoted so '*' reaches az literally instead of globbing to filenames
    az network nsg rule create -g "$RG" --nsg-name "$NSG_NAME" -n "$NSG_RULE_NAME" \
        --priority "$PRIORITY" --direction "$DIRECTION" --access "$ACCESS" --protocol "$PROTOCOL" \
        --source-address-prefixes "$HOME_IP/$SRC_MASK" --source-port-ranges "$SRC_PORT_RANGES" \
        --destination-address-prefixes "$DST_ADDR_PREFIXES" --destination-port-ranges "$DST_PORT_RANGES" -o none
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
    create_nsg
    
    NSG_RULE_NAME=AllowSshFromHome
    PRIORITY=100
    DIRECTION=Inbound
    ACCESS=Allow
    PROTOCOL=Tcp
    SRC_MASK=32
    SRC_PORT_RANGES='*'
    DST_ADDR_PREFIXES='*'
    DST_PORT_RANGES=22
    configure_nsg_rule


}

main