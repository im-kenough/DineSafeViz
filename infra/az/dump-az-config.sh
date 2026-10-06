#!/bin/bash
# Dump the stg and prod Azure configuration to Markdown for documentation.
# Read-only: lists names, settings, tags, locks, and role assignments.
# Secret values are never read; only secret names and dates.
#
# Usage:
#   ./dump-az-config.sh [out-dir]              # both environments, default ./az-config
#   ENV=prod01 ./dump-az-config.sh [out-dir]   # one environment
#   NO_REDACT=1 ./dump-az-config.sh            # keep subscription IDs and IP addresses
#
# Sign in first with az login. dsv-ops01 is enough, and it's the only account
# that can list secret names. Sections the account can't read are recorded as
# "Not available" instead of stopping the dump.
set -euo pipefail

OUT_DIR=${1:-az-config}
ENVS=${ENV:-stg01 prod01}

#################################
# Helpers
#################################
# section <title> <command...>: run a read-only command and append its output
# to $FILE as a fenced block. stderr is kept apart, so CLI warnings (such as
# "This command is in preview") don't end up in the block or hide the error.
section(){
    local title=$1; shift
    local out err rc
    err=$(mktemp)
    {
        echo "## $title"
        echo ""
        if out=$("$@" 2>"$err"); then
            echo '```text'
            if [[ -n $out ]]; then echo "$out"; else echo "(none)"; fi
            echo '```'
        else
            rc=$?
            echo "Not available: $(grep -v -m 1 -e '^WARNING:' -e '^[[:space:]]*$' "$err" || echo "exit code $rc")"
        fi
        echo ""
    } >> "$FILE"
    rm -f "$err"
}

# redact <value> <label>: replace every occurrence of value in $FILE
redact(){
    [[ -n $1 ]] || return 0
    sed -i "s#${1//./\\.}#<$2>#g" "$FILE"
}

#################################
# Dump one environment
#################################
dump_env(){
    local env=$1
    local rg=rg-dsv-$env kv=kv-dsv-$env
    local sub tenant kv_id

    # resolve the ID for the signed-in user, since several cached accounts
    # can see a subscription with the same name
    sub=$(az account list --query "[?name=='sub-dsv-$env' && user.name=='$USER_NAME'].id | [0]" -o tsv)
    if [[ -z $sub ]]; then
        echo "Skipping $env: $USER_NAME can't see subscription sub-dsv-$env" >&2
        return
    fi
    local S=(--subscription "$sub")
    tenant=$(az account show "${S[@]}" --query tenantId -o tsv)
    kv_id=$(az keyvault show "${S[@]}" -n "$kv" --query id -o tsv 2>/dev/null || true)

    FILE=$OUT_DIR/$env.md
    {
        echo "# Azure configuration: $env"
        echo ""
        echo "Generated $(date -u '+%B %-d, %Y at %H:%M UTC') by \`infra/az/dump-az-config.sh\`,"
        echo "signed in as \`$USER_NAME\`. Secret values aren't included."
        echo ""
    } > "$FILE"

    echo "Dumping $env to $FILE..."

    # Subscription and resource groups
    section "Subscription" \
        az account show "${S[@]}" --query "{name:name, id:id, state:state, tenant:tenantId}" -o table
    section "Resource groups" \
        az group list "${S[@]}" --query "[].{name:name, location:location}" -o table
    section "Resources" \
        az resource list "${S[@]}" --query "sort_by(@, &resourceGroup)[].{name:name, type:type, group:resourceGroup, location:location}" -o table
    section "Resource group tags" \
        az group list "${S[@]}" --query "[].{name:name, tags:tags}" -o jsonc
    section "Resource tags" \
        az resource list "${S[@]}" --query "[].{name:name, tags:tags}" -o jsonc
    section "Locks" \
        az lock list "${S[@]}" --query "[].{name:name, level:level, scope:id, notes:notes}" -o table

    # Network
    section "Network security group rules" \
        az network nsg rule list "${S[@]}" -g "$rg" --nsg-name "nsg-dsv-$env-app" -o table
    section "Virtual networks" \
        az network vnet list "${S[@]}" -g "$rg" --query "[].{name:name, addressSpace:join(', ', addressSpace.addressPrefixes)}" -o table
    section "Subnets" \
        az network vnet subnet list "${S[@]}" -g "$rg" --vnet-name "vnet-dsv-$env" \
        --query "[].{name:name, prefix:addressPrefix, nsg:networkSecurityGroup.id, serviceEndpoints:join(', ', serviceEndpoints[].service || \`[]\`)}" -o table
    section "Public IP addresses" \
        az network public-ip list "${S[@]}" -g "$rg" --query "[].{name:name, sku:sku.name, allocation:publicIPAllocationMethod, version:publicIPAddressVersion, address:ipAddress}" -o table
    section "Network interfaces" \
        az network nic list "${S[@]}" -g "$rg" --query "[].{name:name, privateIp:ipConfigurations[0].privateIPAddress, subnet:ipConfigurations[0].subnet.id, nicNsg:networkSecurityGroup.id}" -o table

    # Compute
    section "Virtual machines" \
        az vm list "${S[@]}" -g "$rg" --query "[].{name:name, size:hardwareProfile.vmSize, securityType:securityProfile.securityType, osDisk:storageProfile.osDisk.name, osDiskDelete:storageProfile.osDisk.deleteOption, identity:identity.type}" -o table
    # az disk list requires -g (CLI 2.90); all disks live in $rg
    section "Disks in $rg" \
        az disk list "${S[@]}" -g "$rg" --query "[].{name:name, group:resourceGroup, sku:sku.name, sizeGb:diskSizeGB, state:diskState}" -o table
    section "Snapshots" \
        az snapshot list "${S[@]}" --query "sort_by(@, &timeCreated)[].{name:name, group:resourceGroup, incremental:incremental, created:timeCreated}" -o table

    # Identity and access
    section "Managed identities" \
        az identity list "${S[@]}" -g "$rg" --query "[].{name:name, clientId:clientId, principalId:principalId}" -o table
    section "Role assignments on $rg (including inherited)" \
        az role assignment list "${S[@]}" -g "$rg" --include-inherited --query "[].{principal:principalName, principalId:principalId, type:principalType, role:roleDefinitionName, scope:scope}" -o table

    # Key vault
    section "Key vault" \
        az keyvault show "${S[@]}" -n "$kv" --query "{name:name, sku:properties.sku.name, rbac:properties.enableRbacAuthorization, softDeleteDays:properties.softDeleteRetentionInDays, purgeProtection:properties.enablePurgeProtection, publicNetworkAccess:properties.publicNetworkAccess, defaultAction:properties.networkAcls.defaultAction, bypass:properties.networkAcls.bypass}" -o table
    section "Key vault network rules" \
        az keyvault network-rule list "${S[@]}" -n "$kv" -o jsonc
    if [[ -n $kv_id ]]; then
        section "Role assignments on $kv" \
            az role assignment list "${S[@]}" --scope "$kv_id" --query "[].{principal:principalName, principalId:principalId, type:principalType, role:roleDefinitionName}" -o table
    fi
    section "Key vault secret names" \
        az keyvault secret list "${S[@]}" --vault-name "$kv" --query "[].{name:name, enabled:attributes.enabled, updated:attributes.updated}" -o table

    # Cost
    section "Budgets" \
        az consumption budget list "${S[@]}" --query "[].{name:name, amount:amount, timeGrain:timeGrain}" -o table

    if [[ -z ${NO_REDACT:-} ]]; then
        redact "$sub" subscription-id
        redact "$tenant" tenant-id
        # home IP from the vault firewall and NSG, plus any VM public IP
        local ip
        for ip in $( {
                az keyvault network-rule list "${S[@]}" -n "$kv" --query "ipRules[].value" -o tsv
                az network nsg rule list "${S[@]}" -g "$rg" --nsg-name "nsg-dsv-$env-app" \
                    --query "[[].sourceAddressPrefix, [].sourceAddressPrefixes[]][]" -o tsv
                az network public-ip list "${S[@]}" -g "$rg" --query "[].ipAddress" -o tsv
            } 2>/dev/null | sed 's#/32$##' | grep -E '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' | sort -u || true ); do
            redact "$ip" redacted-ip
        done
    fi
}

main(){
    USER_NAME=$(az account show --query user.name -o tsv 2>/dev/null) || {
        echo "ERROR: not signed in. Run az login first." >&2
        exit 1
    }
    mkdir -p "$OUT_DIR"
    for env in $ENVS; do
        dump_env "$env"
    done
    echo "Done. Review $OUT_DIR before you commit it."
}

main "$@"
