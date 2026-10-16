#!/bin/bash
# Delete vm-dsv-stg01 and its disks (OS and any data disks), leaving
# nic-dsv-stg01 and pip-dsv-stg01 in place for create-stg-vm.sh to reuse.
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

DRY_RUN=${DRY_RUN:-}
YES=${YES:-}

# found by find_disks
DISK_IDS=()

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

check_vm_exists(){
    az vm show -g "$RG" -n "$VM_NAME" -o none 2>/dev/null \
        || die "VM $VM_NAME not found in $RG"
}

find_disks(){
    # read before the delete; afterwards the VM can't tell us
    mapfile -t DISK_IDS < <(az vm show -g "$RG" -n "$VM_NAME" \
        --query "[storageProfile.osDisk.managedDisk.id, storageProfile.dataDisks[].managedDisk.id][]" \
        -o tsv)
}

show_plan(){
    echo "About to delete from $RG:"
    echo "  VM:     $VM_NAME"
    local id
    for id in "${DISK_IDS[@]}"; do
        echo "  Disk:   ${id##*/}"
    done
    echo "Keeping:"
    az vm show -g "$RG" -n "$VM_NAME" \
        --query "networkProfile.networkInterfaces[].id" -o tsv \
        | while read -r nic; do
            echo "  NIC:    ${nic##*/}"
        done
}

confirm(){
    [[ -n $YES || -n $DRY_RUN ]] && return
    local answer
    read -r -p "Type the VM name to confirm: " answer
    [[ $answer == "$VM_NAME" ]] || die "confirmation didn't match, nothing deleted"
}

detach_nics(){
    # a VM created with --nic-delete-option Delete takes its NIC with it;
    # switch every NIC to Detach first so the NIC and public IP survive
    echo "Setting NIC delete option to Detach..."
    local count i
    count=$(az vm show -g "$RG" -n "$VM_NAME" \
        --query "length(networkProfile.networkInterfaces)" -o tsv)
    for (( i = 0; i < count; i++ )); do
        run_az vm update -g "$RG" -n "$VM_NAME" \
            --set "networkProfile.networkInterfaces[$i].deleteOption=Detach" -o none
    done
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
    find_disks
    show_plan
    confirm
    detach_nics
    delete_vm
    delete_disks
    show_remaining
    echo "Done."
}

main "$@"
