#!/bin/bash
# Create vm01-dsv-prod01 on the existing nic-dsv-prod01 (and its public IP,
# pip-dsv-prod01), so the VM keeps the same address every time it's rebuilt,
# and enroll it in the mc-dsv-prod01-vms01 patch schedule. Then gives
# sg-dsv-prod01-operators "Virtual Machine Contributor" on the VM and adds
# "Host vm01-dsv-prod01" to your SSH config.
# By default it attaches the OS disk (osdisk-vm01-dsv-prod01) that
# delete-prod-vm.sh left behind, so the VM comes back as it was. If the disk
# is gone, it creates it from the newest snapshot of it in
# rg-dsv-prod01-snapshots first, and stops if there is no snapshot either.
# With --overwrite it builds a fresh VM from the Ubuntu image instead, after
# deleting the old OS disk (it asks first), and installs the repo's read-only
# deploy key for the admin user so you can ssh in and git clone over SSH.
# Snapshots are never touched. The disk is kept when the VM is deleted.
# A VM on an attached disk has no osProfile, so Azure may refuse the patch
# settings the schedule needs; the script then only warns, and the VM may not
# be patched by mc-dsv-prod01-vms01 (issue #302 moves to a data disk to fix it).
# Run it as dsv-admin01; it refuses any other account. It also stops if the
# resource group has a lock.
# Pair with delete-prod-vm.sh, which removes the VM but leaves the disk, NIC
# and public IP.
#
# Usage:
#   ./create-prod-vm.sh              # attach the existing disk (or restore it from a snapshot)
#   ./create-prod-vm.sh --overwrite  # delete the old disk and build a fresh VM
#   DRY_RUN=1 ./create-prod-vm.sh    # check prerequisites, print the commands
#   YES=1 ./create-prod-vm.sh        # skip the --overwrite prompt
# shellcheck disable=SC2086  # $TAGS is word-split on purpose
set -euo pipefail

#################################
# Variables
#################################
SUB_ID=a3c53ab4-7208-4b24-bddb-2118dd7b2206   # sub-dsv-prod01
LOC=canadacentral
RG=rg-dsv-prod01
SNAP_RG=rg-dsv-prod01-snapshots

VM_NAME=vm01-dsv-prod01
NIC_NAME=nic-dsv-prod01
MI_NAME=id-dsv-prod01-vm
OS_DISK_NAME=osdisk-vm01-dsv-prod01
MC_NAME=mc-dsv-prod01-vms01
MC_ASSIGNMENT_NAME=${MC_NAME}assignment   # the name the portal gave it

SIZE=Standard_B2ats_v2
IMAGE=Canonical:ubuntu-24_04-lts:server:latest
OS_DISK_SIZE_GB=64
STORAGE_SKU=Premium_LRS

ADMIN_USER=dsv-vm-admin
ADMIN_ACCOUNT=dsv-admin01@dinesafevizoutlook.onmicrosoft.com
SSH_KEY=$HOME/.ssh/id_ed25519_dsv_prod01_az_admin.pub
TAGS="workload=dsv env=prod owner=dsv-admin01 managed-by=manual"

# the operators group gets this role on the VM
OPS_GROUP=sg-dsv-prod01-operators
OPS_ROLE="Virtual Machine Contributor"

# read-only deploy key for REPO; it goes to the admin user's ~/.ssh on the VM
DEPLOY_KEY=$HOME/.ssh/dsv-deploy-key-RO
REPO=im-kenough/DineSafeViz
SSH_CONFIG=$HOME/.ssh/config

DRY_RUN=${DRY_RUN:-}
YES=${YES:-}
OVERWRITE=""

OS_DISK_ID=/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/disks/$OS_DISK_NAME
VM_ID=/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$VM_NAME

# found by check_prerequisites
DISK_EXISTS=""
SNAPSHOT_ID=""
PATCH_WARNING=""

# shellcheck source=infra/az/vm-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/vm-lib.sh"

#################################
# Steps
#################################
parse_args(){
    while (( $# )); do
        case $1 in
            --overwrite) OVERWRITE=1 ;;
            -h|--help) print_usage "${BASH_SOURCE[0]}"; exit 0 ;;
            *) die "unknown argument: $1 (see --help)" ;;
        esac
        shift
    done
}

check_prerequisites(){
    echo "Checking prerequisites in $RG..."
    check_vm_prerequisites

    # kept for grant_ops_access
    OPS_GROUP_ID=$(az ad group show --group "$OPS_GROUP" --query id -o tsv) \
        || die "group $OPS_GROUP not found"

    # the disk must not belong to another VM
    local managed_by
    if managed_by=$(az disk show -g "$RG" -n "$OS_DISK_NAME" --query managedBy -o tsv 2>/dev/null); then
        DISK_EXISTS=1
        [[ -z $managed_by ]] || die "disk $OS_DISK_NAME is already attached to ${managed_by##*/}"
    fi

    if [[ -n $OVERWRITE ]]; then
        [[ -f $SSH_KEY ]] || die "SSH public key $SSH_KEY not found"
        [[ -f $DEPLOY_KEY ]] || die "deploy key $DEPLOY_KEY not found"
    elif [[ -z $DISK_EXISTS ]]; then
        SNAPSHOT_ID=$(latest_disk_snapshot "$OS_DISK_ID")
        [[ -n $SNAPSHOT_ID ]] \
            || die "no disk $OS_DISK_NAME in $RG and no snapshot of it in $SNAP_RG; use --overwrite to build a fresh VM"
    fi
    echo "Prerequisites OK"
}

delete_old_disk(){
    [[ -n $DISK_EXISTS ]] || return 0
    echo "--overwrite deletes this disk:"
    az disk show -g "$RG" -n "$OS_DISK_NAME" \
        --query "{name:name, sizeGb:diskSizeGB, created:timeCreated, state:diskState}" -o table
    confirm
    echo "Deleting disk $OS_DISK_NAME..."
    run_az disk delete -g "$RG" -n "$OS_DISK_NAME" --yes
}

restore_disk(){
    [[ -z $DISK_EXISTS ]] || { echo "Attaching existing disk $OS_DISK_NAME"; return 0; }
    echo "Creating disk $OS_DISK_NAME from snapshot ${SNAPSHOT_ID##*/}..."
    # the snapshot is of a Trusted Launch VM's disk, so the new disk has to be
    # Gen2 and Trusted Launch too for the VM to take it
    run_az disk create -g "$RG" -n "$OS_DISK_NAME" -l "$LOC" --source "$SNAPSHOT_ID" \
        --sku "$STORAGE_SKU" --os-type Linux --hyper-v-generation V2 \
        --security-type TrustedLaunch --tags $TAGS -o none
}

create_vm(){
    echo "Creating $VM_NAME ($SIZE)..."
    local os_disk
    if [[ -n $OVERWRITE ]]; then
        os_disk=(--image "$IMAGE"
            --os-disk-name "$OS_DISK_NAME" --os-disk-size-gb "$OS_DISK_SIZE_GB"
            --storage-sku "$STORAGE_SKU"
            --admin-username "$ADMIN_USER" --ssh-key-values "$SSH_KEY"
            --patch-mode AutomaticByPlatform)
    else
        # the disk already has the image, admin user and SSH key; there's no
        # osProfile to hold --patch-mode, so it's left out
        os_disk=(--attach-os-disk "$OS_DISK_ID" --os-type linux)
    fi
    # Detach keeps the NIC (and so the public IP) and the OS disk when the VM
    # is deleted
    run_az vm create -g "$RG" -n "$VM_NAME" -l "$LOC" \
        "${os_disk[@]}" --size "$SIZE" \
        --security-type TrustedLaunch --enable-secure-boot true --enable-vtpm true \
        --nics "$NIC_NAME" --nic-delete-option Detach \
        --os-disk-delete-option Detach \
        --assign-identity "$MI_ID" \
        --tags $TAGS -o none
}

# the attached-disk VM has no osProfile, so the patch settings, and maybe the
# enrollment, can fail; warn and carry on rather than leave a half-built VM
attached_disk_step(){
    local step=$1
    if [[ -n $OVERWRITE ]]; then
        "$step"
    elif ! "$step"; then
        PATCH_WARNING=1
        echo "WARNING: $step failed on the attached-disk VM; carrying on" >&2
    fi
}

warn_patching(){
    [[ -n $PATCH_WARNING ]] || return 0
    cat >&2 <<EOM
WARNING: $VM_NAME was built from an attached disk and couldn't get the patch
settings and/or enrollment that $MC_NAME needs, so it may not be patched on
schedule. Check it with:
  az vm show -g $RG -n $VM_NAME --query osProfile.linuxConfiguration.patchSettings
  az maintenance assignment list -g $RG --provider-name Microsoft.Compute \\
      --resource-type virtualMachines --resource-name $VM_NAME -o table
Patch it by hand (sudo apt upgrade) until issue #302 is done, or rebuild with
--overwrite.
EOM
}

grant_ops_access(){
    # a role assignment scoped to the VM may not outlive it, so redo it each
    # build, skipping it if it's still there
    echo "Granting $OPS_ROLE on $VM_NAME to $OPS_GROUP..."
    if [[ -z $DRY_RUN ]] && [[ -n $(az role assignment list --assignee "$OPS_GROUP_ID" \
            --role "$OPS_ROLE" --scope "$VM_ID" --query "[0].id" -o tsv) ]]; then
        echo "$OPS_GROUP already has it, leaving it"
        return
    fi
    run_az role assignment create --assignee-object-id "$OPS_GROUP_ID" \
        --assignee-principal-type Group --role "$OPS_ROLE" --scope "$VM_ID" -o none
}

#################################
# Main
#################################
main(){
    parse_args "$@"
    select_subscription
    check_admin_account
    check_no_locks "$RG"
    check_prerequisites
    if [[ -n $OVERWRITE ]]; then
        delete_old_disk
    else
        restore_disk
    fi
    create_vm
    attached_disk_step configure_patching
    enable_boot_diagnostics
    wait_until_ready
    attached_disk_step enroll_maintenance
    grant_ops_access
    show_vm
    write_ssh_config
    if [[ -n $OVERWRITE ]]; then
        upload_deploy_key
        configure_deploy_key
    fi
    warn_patching
    echo "Done."
}

main "$@"
