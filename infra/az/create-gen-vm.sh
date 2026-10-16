#!/bin/bash
# Create a DineSafeViz VM, with its own public IP and NIC, in an environment
# whose resource group, network, and managed identity already exist
# (azure-checklist.md step 6.3). VMs are numbered: vm01-dsv-stg01,
# vm02-dsv-stg01, ... A stopgap until real IaC; edit the variables below.
# Once the VM is up, adds a "Host <vm>" entry to your SSH config and installs
# the repo's read-only deploy key for the admin user, so you can ssh in and
# git clone over SSH.
#
# Usage:
#   ./create-gen-vm.sh                # create vm01-dsv-stg01
#   VM_NUM=02 ./create-gen-vm.sh      # create vm02-dsv-stg01
#   DRY_RUN=1 ./create-gen-vm.sh      # check prerequisites, print the commands
#   ENV=prod01 SHORT=prod SUB_ID=<id> SIZE=Standard_B2ats_v2 \
#     DELETE_OPTION=Detach ./create-gen-vm.sh
# shellcheck disable=SC2086  # $TAGS is word-split on purpose
set -euo pipefail

#################################
# Variables: change these to swap environments
#################################
SUB_ID=${SUB_ID:-53db2ec0-9b36-42d0-aa0d-7745f6dafe9a}   # sub-dsv-stg01
ENV=${ENV:-stg01}
SHORT=${SHORT:-stg}
LOC=${LOC:-canadacentral}
VM_NUM=${VM_NUM:-02}

# shared by every VM in the environment
RG=${RG:-rg-dsv-$ENV}
VNET_NAME=${VNET_NAME:-vnet-dsv-$ENV}
SUBNET_NAME=${SUBNET_NAME:-snet-dsv-$ENV-app}   # its NSG covers the NIC
MI_NAME=${MI_NAME:-id-dsv-$ENV-vm}

# one per VM
VM_NAME=${VM_NAME:-vm$VM_NUM-dsv-$ENV}
NIC_NAME=${NIC_NAME:-nic$VM_NUM-dsv-$ENV}
PIP_NAME=${PIP_NAME:-pip$VM_NUM-dsv-$ENV}
OS_DISK_NAME=${OS_DISK_NAME:-osdisk$VM_NUM-dsv-$ENV}

SIZE=${SIZE:-Standard_B2als_v2}
IMAGE=${IMAGE:-Canonical:ubuntu-24_04-lts:server:latest}
OS_DISK_SIZE_GB=${OS_DISK_SIZE_GB:-64}
STORAGE_SKU=${STORAGE_SKU:-Premium_LRS}
# Delete: the NIC and disk go with the VM (stg). Detach: they stay (prod).
DELETE_OPTION=${DELETE_OPTION:-Delete}

ADMIN_USER=${ADMIN_USER:-dsv-vm-admin}
SSH_KEY=${SSH_KEY:-$HOME/.ssh/id_ed25519_dsv_${ENV}_az_admin.pub}
TAGS=${TAGS:-"workload=dsv env=$SHORT owner=dsv-admin01 managed-by=manual"}

# read-only deploy key for REPO; it goes to the admin user's ~/.ssh on the VM
DEPLOY_KEY=${DEPLOY_KEY:-$HOME/.ssh/dsv-deploy-key-RO}
REPO=${REPO:-im-kenough/DineSafeViz}
SSH_CONFIG=${SSH_CONFIG:-$HOME/.ssh/config}

DRY_RUN=${DRY_RUN:-}

# shellcheck source=infra/az/vm-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/vm-lib.sh"

#################################
# Steps
#################################
check_prerequisites(){
    echo "Checking prerequisites in $RG..."
    az group show -n "$RG" -o none || die "resource group $RG not found"
    az network vnet subnet show -g "$RG" --vnet-name "$VNET_NAME" -n "$SUBNET_NAME" -o none \
        || die "subnet $VNET_NAME/$SUBNET_NAME not found"
    # kept for create_vm
    MI_ID=$(az identity show -g "$RG" -n "$MI_NAME" --query id -o tsv) \
        || die "identity $MI_NAME not found"
    [[ -f $SSH_KEY ]] || die "SSH public key $SSH_KEY not found"
    [[ -f $DEPLOY_KEY ]] || die "deploy key $DEPLOY_KEY not found"

    if az vm show -g "$RG" -n "$VM_NAME" -o none 2>/dev/null; then
        die "VM $VM_NAME already exists in $RG"
    fi
    if az disk show -g "$RG" -n "$OS_DISK_NAME" -o none 2>/dev/null; then
        die "disk $OS_DISK_NAME already exists in $RG"
    fi
    # a NIC left over from a failed run is reused, but not one another VM owns
    local nic_vm
    nic_vm=$(az network nic show -g "$RG" -n "$NIC_NAME" --query virtualMachine.id -o tsv 2>/dev/null || true)
    [[ -z $nic_vm ]] || die "NIC $NIC_NAME is already attached to ${nic_vm##*/}"

    # an empty result means a typo in SIZE or a size that LOC doesn't offer
    local found
    found=$(az vm list-skus -l "$LOC" --size "$SIZE" --resource-type virtualMachines \
        --query "[?name=='$SIZE'] | length(@)" -o tsv)
    [[ $found -gt 0 ]] || die "size $SIZE isn't available in $LOC"
    echo "Prerequisites OK"
}

create_public_ip(){
    if az network public-ip show -g "$RG" -n "$PIP_NAME" -o none 2>/dev/null; then
        echo "Public IP $PIP_NAME exists, reusing it"
        return
    fi
    # Standard SKU is always static; billed hourly while it exists, attached or not
    echo "Creating public IP $PIP_NAME..."
    run_az network public-ip create -g "$RG" -n "$PIP_NAME" -l "$LOC" \
        --sku Standard --allocation-method Static --version IPv4 \
        --tags $TAGS -o none
}

create_nic(){
    if az network nic show -g "$RG" -n "$NIC_NAME" -o none 2>/dev/null; then
        echo "NIC $NIC_NAME exists, reusing it"
        return
    fi
    # no NSG on the NIC; the subnet's NSG filters its traffic
    echo "Creating NIC $NIC_NAME..."
    run_az network nic create -g "$RG" -n "$NIC_NAME" -l "$LOC" \
        --vnet-name "$VNET_NAME" --subnet "$SUBNET_NAME" \
        --public-ip-address "$PIP_NAME" \
        --tags $TAGS -o none
}

create_vm(){
    echo "Creating $VM_NAME ($SIZE)..."
    run_az vm create -g "$RG" -n "$VM_NAME" -l "$LOC" \
        --image "$IMAGE" --size "$SIZE" \
        --security-type TrustedLaunch --enable-secure-boot true --enable-vtpm true \
        --nics "$NIC_NAME" --nic-delete-option "$DELETE_OPTION" \
        --os-disk-name "$OS_DISK_NAME" --os-disk-size-gb "$OS_DISK_SIZE_GB" \
        --storage-sku "$STORAGE_SKU" --os-disk-delete-option "$DELETE_OPTION" \
        --admin-username "$ADMIN_USER" --ssh-key-values "$SSH_KEY" \
        --assign-identity "$MI_ID" --patch-mode AutomaticByPlatform \
        --tags $TAGS -o none
}

#################################
# Main
#################################
main(){
    select_subscription
    check_prerequisites
    create_public_ip
    create_nic
    create_vm
    configure_patching
    enable_boot_diagnostics
    show_vm
    write_ssh_config
    upload_deploy_key
    configure_deploy_key
    echo "Done."
}

main "$@"
