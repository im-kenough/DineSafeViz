#!/bin/bash
# Delete a DineSafeViz VM that create-vm.sh made, plus its NIC and public IP.
# The OS disk goes with the VM or stays, depending on its delete option.
# If the VM is gone (e.g. a failed create), the NIC and public IP named for
# VM_NUM are cleaned up instead. A stopgap until real IaC.
#
# Usage:
#   ./delete-vm.sh                # delete vm01-dsv-stg01, after a prompt
#   VM_NUM=02 ./delete-vm.sh      # delete vm02-dsv-stg01
#   VM_NAME=vm-dsv-stg01 ./delete-vm.sh   # a VM named before the numbering
#   DRY_RUN=1 ./delete-vm.sh      # show what would be deleted, delete nothing
#   YES=1 ./delete-vm.sh          # skip the prompt
set -euo pipefail

#################################
# Variables: change these to swap environments
#################################
SUB_ID=${SUB_ID:-53db2ec0-9b36-42d0-aa0d-7745f6dafe9a}   # sub-dsv-stg01
ENV=${ENV:-stg01}
VM_NUM=${VM_NUM:-01}

RG=${RG:-rg-dsv-$ENV}
VM_NAME=${VM_NAME:-vm$VM_NUM-dsv-$ENV}
# only used when the VM no longer exists
NIC_NAME=${NIC_NAME:-nic$VM_NUM-dsv-$ENV}

DRY_RUN=${DRY_RUN:-}
YES=${YES:-}

# found by find_resources
VM_ID=""
NIC_ID=""
PIP_ID=""

#################################
# Helpers
#################################
die(){
    echo "ERROR: $*" >&2
    exit 1
}

# Runs "az <args>", or only prints it when DRY_RUN is set.
run_az(){
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] az $*"
    else
        az "$@"
    fi
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

find_resources(){
    # follow the links VM -> NIC -> public IP, so names don't have to match
    VM_ID=$(az vm show -g "$RG" -n "$VM_NAME" --query id -o tsv 2>/dev/null || true)
    if [[ -n $VM_ID ]]; then
        NIC_ID=$(az vm show --ids "$VM_ID" \
            --query "networkProfile.networkInterfaces[0].id" -o tsv)
    else
        NIC_ID=$(az network nic show -g "$RG" -n "$NIC_NAME" --query id -o tsv 2>/dev/null || true)
    fi
    if [[ -n $NIC_ID ]]; then
        PIP_ID=$(az network nic show --ids "$NIC_ID" \
            --query "ipConfigurations[0].publicIPAddress.id" -o tsv)
    fi
    [[ -n $VM_ID || -n $NIC_ID ]] || die "neither VM $VM_NAME nor NIC $NIC_NAME found in $RG"
}

show_plan(){
    echo "About to delete from $RG:"
    if [[ -n $VM_ID ]]; then
        echo "  VM:        $VM_NAME"
        local disk option
        disk=$(az vm show --ids "$VM_ID" --query storageProfile.osDisk.name -o tsv)
        option=$(az vm show --ids "$VM_ID" --query storageProfile.osDisk.deleteOption -o tsv)
        if [[ $option == Delete ]]; then
            echo "  OS disk:   $disk"
        else
            echo "  OS disk:   $disk is KEPT (delete option $option)"
        fi
    else
        echo "  VM:        $VM_NAME not found, cleaning up what's left"
    fi
    echo "  NIC:       ${NIC_ID##*/}"
    echo "  Public IP: ${PIP_ID##*/}"
}

confirm(){
    [[ -n $YES || -n $DRY_RUN ]] && return
    local answer
    read -r -p "Type the VM name to confirm: " answer
    [[ $answer == "$VM_NAME" ]] || die "confirmation didn't match, nothing deleted"
}

delete_resources(){
    # order matters: a NIC can't go while a VM uses it, nor an IP while a NIC does
    if [[ -n $VM_ID ]]; then
        echo "Deleting VM $VM_NAME..."
        run_az vm delete --ids "$VM_ID" --yes
    fi
    # the NIC may already be gone with the VM (delete option Delete)
    if [[ -n $NIC_ID ]] && az network nic show --ids "$NIC_ID" -o none 2>/dev/null; then
        echo "Deleting NIC ${NIC_ID##*/}..."
        run_az network nic delete --ids "$NIC_ID"
    fi
    if [[ -n $PIP_ID ]]; then
        echo "Deleting public IP ${PIP_ID##*/}..."
        run_az network public-ip delete --ids "$PIP_ID"
    fi
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
    find_resources
    show_plan
    confirm
    delete_resources
    show_remaining
    echo "Done."
}

main "$@"
