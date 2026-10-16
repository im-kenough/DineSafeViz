#!/bin/bash
# Delete vm-dsv-stg01 and its disks (OS and any data disks), leaving
# nic-dsv-stg01 and pip-dsv-stg01 in place for create-stg-vm.sh to reuse.
# Also removes the VM's IP from ~/.ssh/known_hosts and its Host entry
# from ~/.ssh/config.
# For other VMs use delete-gen-vm.sh.
#
# Usage:
#   ./delete-stg-vm.sh            # delete vm-dsv-stg01, after a prompt
#   DRY_RUN=1 ./delete-stg-vm.sh  # show what would be deleted, delete nothing
#   YES=1 ./delete-stg-vm.sh      # skip the prompt
set -euo pipefail

#################################
# Variables
#################################
SUB_ID=53db2ec0-9b36-42d0-aa0d-7745f6dafe9a   # sub-dsv-stg01
RG=rg-dsv-stg01
VM_NAME=vm-dsv-stg01
SSH_CONFIG=$HOME/.ssh/config

DRY_RUN=${DRY_RUN:-}
YES=${YES:-}

# found by find_vm
DISK_IDS=()
NIC_IDS=()
VM_IP=""

# shellcheck source=infra/az/vm-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/vm-lib.sh"

#################################
# Steps
#################################
find_vm(){
    # read before the delete; afterwards the VM can't tell us
    local disks
    disks=$(az vm show -g "$RG" -n "$VM_NAME" \
        --query "[storageProfile.osDisk.managedDisk.id, storageProfile.dataDisks[].managedDisk.id][]" \
        -o tsv 2>/dev/null) || die "VM $VM_NAME not found in $RG"
    mapfile -t DISK_IDS <<<"$disks"
    mapfile -t NIC_IDS < <(az vm show -g "$RG" -n "$VM_NAME" \
        --query "networkProfile.networkInterfaces[].id" -o tsv)
    VM_IP=$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv)
}

show_plan(){
    echo "About to delete from $RG:"
    echo "  VM:     $VM_NAME"
    local id
    for id in "${DISK_IDS[@]}"; do
        echo "  Disk:   ${id##*/}"
    done
    echo "Keeping:"
    for id in "${NIC_IDS[@]}"; do
        echo "  NIC:    ${id##*/}"
    done
    [[ -z $VM_IP ]] || echo "Removing $VM_IP from ~/.ssh/known_hosts"
    if has_ssh_config_entry; then
        echo "Removing Host $VM_NAME from $SSH_CONFIG"
    fi
}

detach_nics(){
    # a VM created with --nic-delete-option Delete takes its NIC with it;
    # switch every NIC to Detach first so the NIC and public IP survive
    echo "Setting NIC delete option to Detach..."
    # one update for all of them; each one is a full PUT of the VM
    local sets=() i
    for i in "${!NIC_IDS[@]}"; do
        sets+=("networkProfile.networkInterfaces[$i].deleteOption=Detach")
    done
    run_az vm update -g "$RG" -n "$VM_NAME" --set "${sets[@]}" -o none
}

delete_vm(){
    echo "Deleting VM $VM_NAME..."
    run_az vm delete -g "$RG" -n "$VM_NAME" --yes
}

delete_disks(){
    # disks with delete option Delete are already gone; delete the rest
    local id
    for id in "${DISK_IDS[@]}"; do
        if az disk show --ids "$id" -o none 2>/dev/null; then
            echo "Deleting disk ${id##*/}..."
            run_az disk delete --ids "$id" --yes
        fi
    done
}

#################################
# Main
#################################
main(){
    select_subscription
    find_vm
    show_plan
    confirm
    detach_nics
    delete_vm
    delete_disks
    forget_host_key
    forget_ssh_config
    show_remaining
    echo "Done."
}

main "$@"
