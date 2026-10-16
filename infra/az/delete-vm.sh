#!/bin/bash
# Delete the DineSafeViz VM that create-vm.sh made. The NIC and OS disk
# go with it or stay, depending on the delete options set at create time.
# A stopgap until real IaC; edit the variables below to target another env.
#
# Usage:
#   ./delete-vm.sh                # delete the stg VM, after a prompt
#   DRY_RUN=1 ./delete-vm.sh      # show what would be deleted, delete nothing
#   YES=1 ./delete-vm.sh          # skip the prompt
#   ENV=prod01 SUB_ID=<id> ./delete-vm.sh
set -euo pipefail

#################################
# Variables: change these to swap environments
#################################
SUB_ID=${SUB_ID:-53db2ec0-9b36-42d0-aa0d-7745f6dafe9a}   # sub-dsv-stg01
ENV=${ENV:-stg01}

RG=${RG:-rg-dsv-$ENV}
VM_NAME=${VM_NAME:-vm-dsv-$ENV}

DRY_RUN=${DRY_RUN:-}
YES=${YES:-}

#################################
# Helpers
#################################
die(){
    echo "ERROR: $*" >&2
    exit 1
}

#################################
# Steps
#################################
select_subscription(){
    # by ID: both the admin and ops accounts cache subs with the same names
    az account show -o none 2>/dev/null || die "not signed in; run 'az login' first"
    az account set --subscription "$SUB_ID"
    echo "Signed in as $(az account show --query user.name -o tsv)," \
        "subscription $(az account show --query name -o tsv)"
}

check_vm_exists(){
    az vm show -g "$RG" -n "$VM_NAME" -o none 2>/dev/null \
        || die "VM $VM_NAME not found in $RG"
}

show_plan(){
    # Delete removes the resource with the VM; Detach leaves it behind
    echo "About to delete $VM_NAME in $RG:"
    az vm show -g "$RG" -n "$VM_NAME" --query "{
        nic: networkProfile.networkInterfaces[0].id,
        nicOnDelete: networkProfile.networkInterfaces[0].deleteOption,
        osDisk: storageProfile.osDisk.name,
        osDiskOnDelete: storageProfile.osDisk.deleteOption}" -o yaml
}

confirm(){
    [[ -n $YES || -n $DRY_RUN ]] && return
    local answer
    read -r -p "Type the VM name to confirm: " answer
    [[ $answer == "$VM_NAME" ]] || die "confirmation didn't match, nothing deleted"
}

delete_vm(){
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] az vm delete -g $RG -n $VM_NAME --yes"
        return
    fi
    echo "Deleting $VM_NAME..."
    az vm delete -g "$RG" -n "$VM_NAME" --yes
}

show_remaining(){
    [[ -n $DRY_RUN ]] && return
    echo "Resources left in $RG:"
    az resource list -g "$RG" --query "[].{name:name, type:type}" -o table
}

#################################
# Main
#################################
main(){
    select_subscription
    check_vm_exists
    show_plan
    confirm
    delete_vm
    show_remaining
    echo "Done."
}

main "$@"
