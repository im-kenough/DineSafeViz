#!/bin/bash
# Create vm-dsv-stg01 on the existing nic-dsv-stg01 (and its public IP,
# pip-dsv-stg01), so the VM keeps the same address every time it's rebuilt,
# and enroll it in the mc-dsv-stg01-vms01 patch schedule. Then adds
# "Host vm-dsv-stg01" to your SSH config and installs the repo's read-only
# deploy key for the admin user, so you can ssh in and git clone over SSH.
# Pair with delete-stg-vm.sh, which removes the VM and its disks but leaves
# the NIC and public IP. For other VMs use create-gen-vm.sh.
#
# Usage:
#   ./create-stg-vm.sh            # create vm-dsv-stg01
#   DRY_RUN=1 ./create-stg-vm.sh  # check prerequisites, print the commands
# shellcheck disable=SC2086  # $TAGS is word-split on purpose
set -euo pipefail

#################################
# Variables
#################################
SUB_ID=53db2ec0-9b36-42d0-aa0d-7745f6dafe9a   # sub-dsv-stg01
LOC=canadacentral
RG=rg-dsv-stg01

VM_NAME=vm-dsv-stg01
NIC_NAME=nic-dsv-stg01
MI_NAME=id-dsv-stg01-vm
OS_DISK_NAME=osdisk-dsv-stg01
MC_NAME=mc-dsv-stg01-vms01
MC_ASSIGNMENT_NAME=${MC_NAME}assignment   # the name the portal gave it

SIZE=Standard_B2als_v2
IMAGE=Canonical:ubuntu-24_04-lts:server:latest
OS_DISK_SIZE_GB=64
STORAGE_SKU=Premium_LRS

ADMIN_USER=dsv-vm-admin
SSH_KEY=$HOME/.ssh/id_ed25519_dsv_stg01_az_admin.pub
TAGS="workload=dsv env=stg owner=dsv-admin01 managed-by=manual"

# read-only deploy key for REPO; it goes to the admin user's ~/.ssh on the VM
DEPLOY_KEY=$HOME/.ssh/dsv-deploy-key-RO
REPO=im-kenough/DineSafeViz
SSH_CONFIG=$HOME/.ssh/config

DRY_RUN=${DRY_RUN:-}

# shellcheck source=infra/az/vm-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/vm-lib.sh"

#################################
# Steps
#################################
check_prerequisites(){
    echo "Checking prerequisites in $RG..."
    # kept for create_vm
    MI_ID=$(az identity show -g "$RG" -n "$MI_NAME" --query id -o tsv) \
        || die "identity $MI_NAME not found"
    az extension show -n maintenance -o none 2>/dev/null \
        || die "az maintenance extension missing; run 'az extension add -n maintenance'"
    # kept for enroll_maintenance
    MC_ID=$(az maintenance configuration show -g "$RG" --resource-name "$MC_NAME" --query id -o tsv) \
        || die "maintenance configuration $MC_NAME not found"
    [[ -f $SSH_KEY ]] || die "SSH public key $SSH_KEY not found"
    [[ -f $DEPLOY_KEY ]] || die "deploy key $DEPLOY_KEY not found"

    if az vm show -g "$RG" -n "$VM_NAME" -o none 2>/dev/null; then
        die "VM $VM_NAME already exists in $RG"
    fi
    if az disk show -g "$RG" -n "$OS_DISK_NAME" -o none 2>/dev/null; then
        die "disk $OS_DISK_NAME already exists in $RG"
    fi

    # the NIC must be there, and free
    local nic_vm
    nic_vm=$(az network nic show -g "$RG" -n "$NIC_NAME" --query virtualMachine.id -o tsv 2>/dev/null) \
        || die "NIC $NIC_NAME not found"
    [[ -z $nic_vm ]] || die "NIC $NIC_NAME is already attached to ${nic_vm##*/}"
    echo "Prerequisites OK"
}

create_vm(){
    echo "Creating $VM_NAME ($SIZE)..."
    # Detach keeps the NIC (and so the public IP) when the VM is deleted;
    # Delete removes the OS disk with it
    run_az vm create -g "$RG" -n "$VM_NAME" -l "$LOC" \
        --image "$IMAGE" --size "$SIZE" \
        --security-type TrustedLaunch --enable-secure-boot true --enable-vtpm true \
        --nics "$NIC_NAME" --nic-delete-option Detach \
        --os-disk-name "$OS_DISK_NAME" --os-disk-size-gb "$OS_DISK_SIZE_GB" \
        --storage-sku "$STORAGE_SKU" --os-disk-delete-option Delete \
        --admin-username "$ADMIN_USER" --ssh-key-values "$SSH_KEY" \
        --assign-identity "$MI_ID" --patch-mode AutomaticByPlatform \
        --tags $TAGS -o none
}

wait_until_ready(){
    # the patch settings update must finish before the VM can be enrolled
    echo "Waiting for $VM_NAME to finish provisioning..."
    run_az vm wait -g "$RG" -n "$VM_NAME" --updated
}

enroll_maintenance(){
    # the enrollment goes with the VM when it's deleted, so redo it each build
    echo "Enrolling $VM_NAME in $MC_NAME..."
    run_az maintenance assignment create -g "$RG" -n "$MC_ASSIGNMENT_NAME" -l "$LOC" \
        --provider-name Microsoft.Compute --resource-type virtualMachines \
        --resource-name "$VM_NAME" --maintenance-configuration-id "$MC_ID" -o none
}

#################################
# Main
#################################
main(){
    select_subscription
    check_prerequisites
    create_vm
    configure_patching
    enable_boot_diagnostics
    wait_until_ready
    enroll_maintenance
    show_vm
    write_ssh_config
    upload_deploy_key
    configure_deploy_key
    echo "Done."
}

main "$@"
