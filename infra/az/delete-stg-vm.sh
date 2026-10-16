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

# found by find_disks and find_ip
DISK_IDS=()
VM_IP=""

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

# True if SSH_CONFIG has a "Host $VM_NAME" block.
has_ssh_config_entry(){
    grep -qiE "^Host[[:space:]]+${VM_NAME}[[:space:]]*\$" "$SSH_CONFIG" 2>/dev/null
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

find_ip(){
    # read before the delete, for forget_host_key
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
    az vm show -g "$RG" -n "$VM_NAME" \
        --query "networkProfile.networkInterfaces[].id" -o tsv \
        | while read -r nic; do
            echo "  NIC:    ${nic##*/}"
        done
    [[ -z $VM_IP ]] || echo "Removing $VM_IP from ~/.ssh/known_hosts"
    if has_ssh_config_entry; then
        echo "Removing Host $VM_NAME from $SSH_CONFIG"
    fi
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

forget_host_key(){
    # the next VM on this IP has a new host key, so the saved one is useless
    [[ -n $VM_IP ]] || return 0
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] ssh-keygen -R $VM_IP"
        return
    fi
    echo "Removing $VM_IP from ~/.ssh/known_hosts..."
    ssh-keygen -R "$VM_IP" >/dev/null 2>&1 || true
}

# Removes the "Host $VM_NAME" block that create-*-vm.sh added (or one you
# wrote) from SSH_CONFIG, with the comments and blank lines just above it.
# The next create adds a fresh one.
forget_ssh_config(){
    has_ssh_config_entry || return 0
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] remove Host $VM_NAME from $SSH_CONFIG"
        return
    fi
    echo "Removing Host $VM_NAME from $SSH_CONFIG (old copy in $SSH_CONFIG.old)..."
    local tmp
    tmp=$(mktemp)
    awk -v host="$VM_NAME" '
        /^[[:space:]]*$/ || /^#/ { held = held $0 "\n"; next }
        tolower($1) == "host" || tolower($1) == "match" {
            skip = tolower($1) == "host" && NF == 2 && $2 == host
            if (skip) { held = ""; next }
            printf "%s", held; held = ""; print; next
        }
        skip { held = ""; next }
        { printf "%s", held; held = ""; print }
        END { if (!skip) printf "%s", held }
    ' "$SSH_CONFIG" > "$tmp"
    cp -p "$SSH_CONFIG" "$SSH_CONFIG.old"
    cat "$tmp" > "$SSH_CONFIG"   # in place, so its mode and any symlink are kept
    rm -f "$tmp"
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
    find_ip
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
