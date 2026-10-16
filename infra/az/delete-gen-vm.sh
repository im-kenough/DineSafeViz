#!/bin/bash
# Delete a DineSafeViz VM that create-gen-vm.sh made, plus its NIC and public IP.
# The OS disk goes with the VM or stays, depending on its delete option.
# If the VM is gone (e.g. a failed create), the NIC and public IP named for
# VM_NUM are cleaned up instead. Also removes the public IP from
# ~/.ssh/known_hosts and the VM's Host entry from ~/.ssh/config.
# A stopgap until real IaC.
#
# Usage:
#   ./delete-gen-vm.sh                # delete vm01-dsv-stg01, after a prompt
#   VM_NUM=02 ./delete-gen-vm.sh      # delete vm02-dsv-stg01
#   VM_NAME=vm-dsv-stg01 ./delete-gen-vm.sh   # a VM named before the numbering
#   DRY_RUN=1 ./delete-gen-vm.sh      # show what would be deleted, delete nothing
#   YES=1 ./delete-gen-vm.sh          # skip the prompt
set -euo pipefail

#################################
# Variables: change these to swap environments
#################################
SUB_ID=${SUB_ID:-53db2ec0-9b36-42d0-aa0d-7745f6dafe9a}   # sub-dsv-stg01
ENV=${ENV:-stg01}
VM_NUM=${VM_NUM:-02}

RG=${RG:-rg-dsv-$ENV}
VM_NAME=${VM_NAME:-vm$VM_NUM-dsv-$ENV}
# only used when the VM no longer exists
NIC_NAME=${NIC_NAME:-nic$VM_NUM-dsv-$ENV}
SSH_CONFIG=${SSH_CONFIG:-$HOME/.ssh/config}

DRY_RUN=${DRY_RUN:-}
YES=${YES:-}

# found by find_resources
VM_ID=""
NIC_ID=""
PIP_ID=""
VM_IP=""

# shellcheck source=infra/az/vm-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/vm-lib.sh"

#################################
# Steps
#################################
find_resources(){
    # follow the links VM -> NIC -> public IP, so names don't have to match
    local vm
    mapfile -t vm < <(az vm show -g "$RG" -n "$VM_NAME" \
        --query "[id, networkProfile.networkInterfaces[0].id]" -o tsv 2>/dev/null || true)
    VM_ID=${vm[0]:-}
    NIC_ID=${vm[1]:-}
    if [[ -z $VM_ID ]]; then
        NIC_ID=$(az network nic show -g "$RG" -n "$NIC_NAME" --query id -o tsv 2>/dev/null || true)
    fi
    if [[ -n $NIC_ID ]]; then
        PIP_ID=$(az network nic show --ids "$NIC_ID" \
            --query "ipConfigurations[0].publicIPAddress.id" -o tsv)
    fi
    if [[ -n $PIP_ID ]]; then
        VM_IP=$(az network public-ip show --ids "$PIP_ID" --query ipAddress -o tsv)
    fi
    [[ -n $VM_ID || -n $NIC_ID ]] || die "neither VM $VM_NAME nor NIC $NIC_NAME found in $RG"
}

show_plan(){
    echo "About to delete from $RG:"
    if [[ -n $VM_ID ]]; then
        echo "  VM:        $VM_NAME"
        local os_disk disk option
        mapfile -t os_disk < <(az vm show --ids "$VM_ID" \
            --query "[storageProfile.osDisk.name, storageProfile.osDisk.deleteOption]" -o tsv)
        disk=${os_disk[0]}
        option=${os_disk[1]}
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
    [[ -z $VM_IP ]] || echo "Removing $VM_IP from ~/.ssh/known_hosts"
    if has_ssh_config_entry; then
        echo "Removing Host $VM_NAME from $SSH_CONFIG"
    fi
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

#################################
# Main
#################################
main(){
    select_subscription
    find_resources
    show_plan
    confirm
    delete_resources
    forget_host_key
    forget_ssh_config
    show_remaining
    echo "Done."
}

main "$@"
