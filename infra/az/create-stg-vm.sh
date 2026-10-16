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
    az identity show -g "$RG" -n "$MI_NAME" -o none || die "identity $MI_NAME not found"
    az extension show -n maintenance -o none 2>/dev/null \
        || die "az maintenance extension missing; run 'az extension add -n maintenance'"
    az maintenance configuration show -g "$RG" --resource-name "$MC_NAME" -o none \
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
    az network nic show -g "$RG" -n "$NIC_NAME" -o none 2>/dev/null \
        || die "NIC $NIC_NAME not found"
    local nic_vm
    nic_vm=$(az network nic show -g "$RG" -n "$NIC_NAME" --query virtualMachine.id -o tsv)
    [[ -z $nic_vm ]] || die "NIC $NIC_NAME is already attached to ${nic_vm##*/}"
    echo "Prerequisites OK"
}

create_vm(){
    echo "Creating $VM_NAME ($SIZE)..."
    local mi_id
    mi_id=$(az identity show -g "$RG" -n "$MI_NAME" --query id -o tsv)

    # Detach keeps the NIC (and so the public IP) when the VM is deleted;
    # Delete removes the OS disk with it
    run_az vm create -g "$RG" -n "$VM_NAME" -l "$LOC" \
        --image "$IMAGE" --size "$SIZE" \
        --security-type TrustedLaunch --enable-secure-boot true --enable-vtpm true \
        --nics "$NIC_NAME" --nic-delete-option Detach \
        --os-disk-name "$OS_DISK_NAME" --os-disk-size-gb "$OS_DISK_SIZE_GB" \
        --storage-sku "$STORAGE_SKU" --os-disk-delete-option Delete \
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

wait_until_ready(){
    # the patch settings update must finish before the VM can be enrolled
    echo "Waiting for $VM_NAME to finish provisioning..."
    run_az vm wait -g "$RG" -n "$VM_NAME" --updated
}

enroll_maintenance(){
    # the enrollment goes with the VM when it's deleted, so redo it each build
    echo "Enrolling $VM_NAME in $MC_NAME..."
    local mc_id
    mc_id=$(az maintenance configuration show -g "$RG" --resource-name "$MC_NAME" --query id -o tsv)
    run_az maintenance assignment create -g "$RG" -n "$MC_ASSIGNMENT_NAME" -l "$LOC" \
        --provider-name Microsoft.Compute --resource-type virtualMachines \
        --resource-name "$VM_NAME" --maintenance-configuration-id "$mc_id" -o none
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
