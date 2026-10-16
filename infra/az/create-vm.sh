#!/bin/bash
# Create the DineSafeViz VM in an environment whose network, NIC, and
# managed identity already exist (azure-checklist.md step 6.3).
# A stopgap until real IaC; edit the variables below to target another env.
#
# Usage:
#   ./create-vm.sh                # create the stg VM
#   DRY_RUN=1 ./create-vm.sh      # check prerequisites, print the commands
#   ENV=prod01 SHORT=prod SUB_ID=<id> SIZE=Standard_B2ats_v2 \
#     DELETE_OPTION=Detach ./create-vm.sh
# shellcheck disable=SC2086  # $TAGS is word-split on purpose
set -euo pipefail

#################################
# Variables: change these to swap environments
#################################
SUB_ID=${SUB_ID:-53db2ec0-9b36-42d0-aa0d-7745f6dafe9a}   # sub-dsv-stg01
ENV=${ENV:-stg01}
SHORT=${SHORT:-stg}
LOC=${LOC:-canadacentral}

RG=${RG:-rg-dsv-$ENV}
VM_NAME=${VM_NAME:-vm-dsv-$ENV}
NIC_NAME=${NIC_NAME:-nic-dsv-$ENV}
MI_NAME=${MI_NAME:-id-dsv-$ENV-vm}
OS_DISK_NAME=${OS_DISK_NAME:-osdisk-dsv-$ENV}

SIZE=${SIZE:-Standard_B2als_v2}
IMAGE=${IMAGE:-Canonical:ubuntu-24_04-lts:server:latest}
OS_DISK_SIZE_GB=${OS_DISK_SIZE_GB:-64}
STORAGE_SKU=${STORAGE_SKU:-Premium_LRS}
# Delete: the NIC and disk go with the VM (stg). Detach: they stay (prod).
DELETE_OPTION=${DELETE_OPTION:-Delete}

ADMIN_USER=${ADMIN_USER:-dsv-vm-admin}
SSH_KEY=${SSH_KEY:-$HOME/.ssh/id_ed25519_dsv_${ENV}_az_admin.pub}
TAGS=${TAGS:-"workload=dsv env=$SHORT owner=dsv-admin01 managed-by=manual"}

DRY_RUN=${DRY_RUN:-}

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

check_prerequisites(){
    echo "Checking prerequisites in $RG..."
    az group show -n "$RG" -o none || die "resource group $RG not found"
    az network nic show -g "$RG" -n "$NIC_NAME" -o none || die "NIC $NIC_NAME not found"
    az identity show -g "$RG" -n "$MI_NAME" -o none || die "identity $MI_NAME not found"
    [[ -f $SSH_KEY ]] || die "SSH public key $SSH_KEY not found"

    if az vm show -g "$RG" -n "$VM_NAME" -o none 2>/dev/null; then
        die "VM $VM_NAME already exists in $RG"
    fi

    # an empty result means a typo in SIZE or a size that LOC doesn't offer
    local found
    found=$(az vm list-skus -l "$LOC" --size "$SIZE" --resource-type virtualMachines \
        --query "[?name=='$SIZE'] | length(@)" -o tsv)
    [[ $found -gt 0 ]] || die "size $SIZE isn't available in $LOC"
    echo "Prerequisites OK"
}

create_vm(){
    echo "Creating $VM_NAME ($SIZE)..."
    local mi_id
    mi_id=$(az identity show -g "$RG" -n "$MI_NAME" --query id -o tsv)

    run_az vm create -g "$RG" -n "$VM_NAME" -l "$LOC" \
        --image "$IMAGE" --size "$SIZE" \
        --security-type TrustedLaunch --enable-secure-boot true --enable-vtpm true \
        --nics "$NIC_NAME" --nic-delete-option "$DELETE_OPTION" \
        --os-disk-name "$OS_DISK_NAME" --os-disk-size-gb "$OS_DISK_SIZE_GB" \
        --storage-sku "$STORAGE_SKU" --os-disk-delete-option "$DELETE_OPTION" \
        --admin-username "$ADMIN_USER" --ssh-key-values "$SSH_KEY" \
        --assign-identity "$mi_id" --patch-mode AutomaticByPlatform \
        --tags $TAGS -o none
}

configure_patching(){
    # az vm create has no options for these; without the bypass flag Azure
    # patches on its own schedule and ignores the maintenance configuration
    echo "Configuring patch settings..."
    run_az vm update -g "$RG" -n "$VM_NAME" --set \
        osProfile.linuxConfiguration.patchSettings.assessmentMode=AutomaticByPlatform \
        'osProfile.linuxConfiguration.patchSettings.automaticByPlatformSettings={"bypassPlatformSafetyChecksOnUserSchedule": true}' \
        -o none
}

enable_boot_diagnostics(){
    # the serial console needs boot diagnostics
    echo "Enabling boot diagnostics..."
    run_az vm boot-diagnostics enable -g "$RG" -n "$VM_NAME" -o none
}

show_vm(){
    [[ -n $DRY_RUN ]] && return
    az vm show -d -g "$RG" -n "$VM_NAME" \
        --query "{name:name, size:hardwareProfile.vmSize, state:powerState, publicIp:publicIps, privateIp:privateIps}" \
        -o table
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
    show_vm
    echo "Done."
}

main "$@"
