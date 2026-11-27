#!/bin/bash
# Delete vm01-dsv-prod01 but keep its OS disk (osdisk-vm01-dsv-prod01), so
# create-prod-vm.sh can attach it again, and keep nic-dsv-prod01 and
# pip-dsv-prod01 for it to reuse. The snapshots in rg-dsv-prod01-snapshots are
# kept too. Also removes the VM's IP from ~/.ssh/known_hosts and its Host entry
# from ~/.ssh/config.
# With --purge it also deletes the OS disk (and any data disks) and every
# snapshot of the OS disk in rg-dsv-prod01-snapshots; the NIC and public IP
# are still kept. If the VM is already gone, --purge deletes the disk and
# snapshots that are left, and without it the script stops.
# Run it as dsv-admin01; it refuses any other account. It also stops if the
# resource group has a lock (the snapshot group too, with --purge).
# Pair with create-prod-vm.sh.
#
# Usage:
#   ./delete-prod-vm.sh                 # delete vm01-dsv-prod01, keep the disk, after a prompt
#   ./delete-prod-vm.sh --purge         # also delete the disk and its snapshots
#   DRY_RUN=1 ./delete-prod-vm.sh       # show what would be deleted, delete nothing
#   YES=1 ./delete-prod-vm.sh           # skip the prompt
set -euo pipefail

#################################
# Variables
#################################
SUB_ID=a3c53ab4-7208-4b24-bddb-2118dd7b2206   # sub-dsv-prod01
RG="rg-dsv-prod01"
SNAP_RG="rg-dsv-prod01-snapshots"
VM_NAME=vm01-dsv-prod01
OS_DISK_NAME=osdisk-vm01-dsv-prod01
ADMIN_ACCOUNT=dsv-admin01@dinesafevizoutlook.onmicrosoft.com
SSH_CONFIG=$HOME/.ssh/config

DRY_RUN=${DRY_RUN:-}
YES=${YES:-}
PURGE=""

# found by find_vm
VM_FOUND=""
OS_DISK_ID=/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/disks/$OS_DISK_NAME
DISK_IDS=()
NIC_IDS=()
SNAPSHOT_IDS=()
VM_IP=""

# shellcheck source=infra/az/vm-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/vm-lib.sh"

#################################
# Steps
#################################
parse_args(){
    while (( $# )); do
        case $1 in
            --purge) PURGE=1 ;;
            -h|--help) print_usage "${BASH_SOURCE[0]}"; exit 0 ;;
            *) die "unknown argument: $1 (see --help)" ;;
        esac
        shift
    done
}

find_vm(){
    # read before the delete; afterwards the VM can't tell us
    local disks
    if disks=$(az vm show -g "$RG" -n "$VM_NAME" \
            --query "[storageProfile.osDisk.managedDisk.id, storageProfile.dataDisks[].managedDisk.id][]" \
            -o tsv 2>/dev/null); then
        VM_FOUND=1
        mapfile -t DISK_IDS <<<"$disks"
        OS_DISK_ID=${DISK_IDS[0]}
        mapfile -t NIC_IDS < <(az vm show -g "$RG" -n "$VM_NAME" \
            --query "networkProfile.networkInterfaces[].id" -o tsv)
        VM_IP=$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv)
    else
        [[ -n $PURGE ]] || die "VM $VM_NAME not found in $RG"
        echo "VM $VM_NAME not found in $RG, purging what is left"
        if az disk show --ids "$OS_DISK_ID" -o none 2>/dev/null; then
            DISK_IDS=("$OS_DISK_ID")
        fi
    fi
    mapfile -t SNAPSHOT_IDS < <(list_disk_snapshots "$OS_DISK_ID")
    if [[ -z $VM_FOUND && ${#DISK_IDS[@]} -eq 0 && ${#SNAPSHOT_IDS[@]} -eq 0 ]]; then
        die "no VM, disk or snapshots left to purge"
    fi
}

list_disks_and_snapshots(){
    local id
    for id in "${DISK_IDS[@]}"; do
        echo "  Disk:     ${id##*/}"
    done
    for id in "${SNAPSHOT_IDS[@]}"; do
        echo "  Snapshot: ${id##*/} (in $SNAP_RG)"
    done
}

show_plan(){
    local id
    echo "About to delete from $RG:"
    [[ -z $VM_FOUND ]] || echo "  VM:       $VM_NAME"
    [[ -z $PURGE ]] || list_disks_and_snapshots
    echo "Keeping:"
    [[ -n $PURGE ]] || list_disks_and_snapshots
    for id in "${NIC_IDS[@]}"; do
        echo "  NIC:      ${id##*/}"
    done
    [[ -z $VM_IP ]] || echo "Removing $VM_IP from ~/.ssh/known_hosts"
    if has_ssh_config_entry; then
        echo "Removing Host $VM_NAME from $SSH_CONFIG"
    fi
}

set_detach_options(){
    # the VM was created with Detach for all of these; set it again so a VM
    # made some other way can't take its disk or NIC with it
    echo "Setting disk and NIC delete options to Detach..."
    # one update for all of them; each one is a full PUT of the VM
    local sets=("storageProfile.osDisk.deleteOption=Detach") i
    # DISK_IDS[0] is the OS disk, the rest are data disks
    for (( i = 1; i < ${#DISK_IDS[@]}; i++ )); do
        sets+=("storageProfile.dataDisks[$((i - 1))].deleteOption=Detach")
    done
    for i in "${!NIC_IDS[@]}"; do
        sets+=("networkProfile.networkInterfaces[$i].deleteOption=Detach")
    done
    run_az vm update -g "$RG" -n "$VM_NAME" --set "${sets[@]}" -o none
}

delete_disks(){
    local id
    for id in "${DISK_IDS[@]}"; do
        echo "Deleting disk ${id##*/}..."
        run_az disk delete --ids "$id" --yes
    done
}

delete_snapshots(){
    local id
    for id in "${SNAPSHOT_IDS[@]}"; do
        echo "Deleting snapshot ${id##*/}..."
        run_az snapshot delete --ids "$id"
    done
}

#################################
# Main
#################################
main(){
    parse_args "$@"
    select_subscription
    check_admin_account
    check_no_locks "$RG" ${PURGE:+"$SNAP_RG"}
    find_vm
    show_plan
    confirm
    if [[ -n $VM_FOUND ]]; then
        set_detach_options
        delete_vm
    fi
    if [[ -n $PURGE ]]; then
        delete_disks
        delete_snapshots
    fi
    forget_host_key
    forget_ssh_config
    show_remaining
    echo "Done."
}

main "$@"
