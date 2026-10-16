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
    az network vnet subnet show -g "$RG" --vnet-name "$VNET_NAME" -n "$SUBNET_NAME" -o none \
        || die "subnet $VNET_NAME/$SUBNET_NAME not found"
    az identity show -g "$RG" -n "$MI_NAME" -o none || die "identity $MI_NAME not found"
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

# Adds a "Host $VM_NAME" entry to SSH_CONFIG, unless there's one already, and
# sets SSH_OPTS for the steps below. SSH_OPTS repeats the entry's settings,
# so a stale entry you wrote yourself can't send them to the wrong host.
write_ssh_config(){
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] add Host $VM_NAME to $SSH_CONFIG"
        return
    fi
    local ip
    ip=$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv)
    [[ -n $ip ]] || die "$VM_NAME has no public IP"
    SSH_OPTS=(-o "HostName=$ip" -o "User=$ADMIN_USER" -i "${SSH_KEY%.pub}"
        -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)

    # the VM is new, so any host key known for its IP is from a deleted VM
    ssh-keygen -R "$ip" >/dev/null 2>&1 || true

    if grep -qE "^Host[[:space:]]+$VM_NAME([[:space:]]|\$)" "$SSH_CONFIG" 2>/dev/null; then
        local current
        current=$(ssh -F "$SSH_CONFIG" -G "$VM_NAME" 2>/dev/null | awk '$1 == "hostname" {print $2}')
        echo "Host $VM_NAME is already in $SSH_CONFIG, leaving it"
        [[ $current == "$ip" ]] \
            || echo "WARNING: that entry points at $current, but $VM_NAME is at $ip" >&2
        return
    fi
    echo "Adding Host $VM_NAME ($ip) to $SSH_CONFIG..."
    cat >> "$SSH_CONFIG" <<CONF

# added by ${0##*/}
Host $VM_NAME
    HostName $ip
    User $ADMIN_USER
    IdentityFile ${SSH_KEY%.pub}
    IdentitiesOnly yes
CONF
    chmod 600 "$SSH_CONFIG"
}

upload_deploy_key(){
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] scp $DEPLOY_KEY $VM_NAME:.ssh/"
        return
    fi
    # sshd can lag a little behind the provisioning state
    echo "Waiting for SSH on $VM_NAME..."
    local i
    for i in {1..12}; do
        ssh "${SSH_OPTS[@]}" -o ConnectTimeout=10 -o BatchMode=yes "$VM_NAME" true 2>/dev/null && break
        [[ $i -lt 12 ]] || die "no SSH to $VM_NAME after 2 minutes"
        sleep 10
    done
    echo "Uploading deploy key ${DEPLOY_KEY##*/}..."
    scp -q "${SSH_OPTS[@]}" "$DEPLOY_KEY" "$VM_NAME:.ssh/${DEPLOY_KEY##*/}"
}

# Locks down the key, points git@github.com at it with GitHub's published host
# keys, and checks that GitHub accepts it.
configure_deploy_key(){
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] configure the deploy key on $VM_NAME"
        return
    fi
    echo "Configuring deploy key on $VM_NAME..."
    local out
    out=$(ssh "${SSH_OPTS[@]}" "$VM_NAME" bash -s -- "${DEPLOY_KEY##*/}" <<'REMOTE'
set -euo pipefail
key=~/.ssh/$1
chmod 700 ~/.ssh
chmod 600 "$key"

# from GitHub's API over HTTPS, instead of trusting whatever answers first
curl -fsS https://api.github.com/meta \
    | python3 -c 'import json, sys; print("\n".join("github.com " + k for k in json.load(sys.stdin)["ssh_keys"]))' \
    > ~/.ssh/known_hosts_github
chmod 600 ~/.ssh/known_hosts_github

if ! grep -qE '^Host[[:space:]]+github\.com([[:space:]]|$)' ~/.ssh/config 2>/dev/null; then
    cat >> ~/.ssh/config <<CONF
Host github.com
    User git
    IdentityFile $key
    IdentitiesOnly yes
    UserKnownHostsFile ~/.ssh/known_hosts_github
    StrictHostKeyChecking yes
CONF
fi
chmod 600 ~/.ssh/config

# exits 1 even when the key is accepted, since GitHub gives no shell
ssh -T git@github.com 2>&1 || true
REMOTE
    )
    grep -q "successfully authenticated" <<<"$out" \
        || die "GitHub didn't accept the deploy key: $out"
    echo "Deploy key OK. To clone: ssh $VM_NAME, then git clone git@github.com:$REPO.git"
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
