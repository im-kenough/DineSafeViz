# shellcheck shell=bash
# Helpers shared by create-*-vm.sh and delete-*-vm.sh. Each function reads the
# globals the calling script sets (SUB_ID, RG, VM_NAME, SSH_CONFIG, DRY_RUN,
# and so on) before main runs.

#################################
# General
#################################
die(){
    echo "ERROR: $*" >&2
    exit 1
}

# Prints the comment block at the top of the script given as $1 (the usage text).
print_usage(){
    awk 'NR == 1 { next } /^# shellcheck/ || !/^#/ { exit } { sub(/^# ?/, ""); print }' "$1"
}

# Runs "az <args>", or only prints it when DRY_RUN is set.
run_az(){
    if [[ -n $DRY_RUN ]]; then
        echo "[dry run] az $*"
    else
        az "$@"
    fi
}

select_subscription(){
    # by ID: both the admin and ops accounts cache subs with the same names
    az account show -o none 2>/dev/null || die "not signed in; run 'az login' first"
    az account set --subscription "$SUB_ID"
    # -o tsv prints a list one item per line
    local account
    mapfile -t account < <(az account show --query "[user.name, name]" -o tsv)
    AZ_USER=${account[0]}   # kept for check_admin_account
    echo "Signed in as $AZ_USER, subscription ${account[1]}"
}

# Refuses to go on unless the user select_subscription signed in as is
# ADMIN_ACCOUNT. Prod operators only have Reader on the resource group, so
# these scripts can't work for them.
check_admin_account(){
    [[ ${AZ_USER,,} == "${ADMIN_ACCOUNT,,}" ]] \
        || die "signed in as $AZ_USER; run this as $ADMIN_ACCOUNT (prod operators only have Reader on $RG)"
}

# Dies if any of the resource groups given as arguments has a lock, before
# anything is changed.
check_no_locks(){
    local rg locks
    for rg in "$@"; do
        locks=$(az lock list -g "$rg" --query "[].join(' ', [name, level])" -o tsv)
        [[ -z $locks ]] || die "resource group $rg has a lock (name, level): ${locks//$'\n'/, }; remove it first"
    done
}

#################################
# Snapshots
#################################
# Prints the IDs of the snapshots in SNAP_RG that were taken from the disk
# with ID $1, oldest first. Azure IDs vary in case, so the match ignores it.
list_disk_snapshots(){
    az snapshot list -g "$SNAP_RG" \
        --query "[].[timeCreated, creationData.sourceResourceId, id]" -o tsv \
        | awk -F'\t' -v disk="$1" 'tolower($2) == tolower(disk) { print $1 "\t" $3 }' \
        | sort | cut -f2
}

# Prints the ID of the newest snapshot of the disk with ID $1, or nothing.
latest_disk_snapshot(){
    list_disk_snapshots "$1" | tail -n 1
}

#################################
# SSH config
#################################
# True if SSH_CONFIG has a "Host $VM_NAME" block.
has_ssh_config_entry(){
    grep -qiE "^Host[[:space:]]+${VM_NAME}[[:space:]]*\$" "$SSH_CONFIG" 2>/dev/null
}

# Prints the HostName that SSH_CONFIG gives VM_NAME.
ssh_config_hostname(){
    ssh -F "$SSH_CONFIG" -G "$VM_NAME" 2>/dev/null | awk '$1 == "hostname" {print $2}'
}

#################################
# Create steps
#################################
# The checks every create-*-vm.sh needs: sets MI_ID (for create_vm) and MC_ID
# (for enroll_maintenance), and dies if VM_NAME exists or NIC_NAME is missing
# or attached to a VM.
check_vm_prerequisites(){
    MI_ID=$(az identity show -g "$RG" -n "$MI_NAME" --query id -o tsv) \
        || die "identity $MI_NAME not found"
    az extension show -n maintenance -o none 2>/dev/null \
        || die "az maintenance extension missing; run 'az extension add -n maintenance'"
    MC_ID=$(az maintenance configuration show -g "$RG" --resource-name "$MC_NAME" --query id -o tsv) \
        || die "maintenance configuration $MC_NAME not found"

    if az vm show -g "$RG" -n "$VM_NAME" -o none 2>/dev/null; then
        die "VM $VM_NAME already exists in $RG"
    fi

    # the NIC must be there, and free
    local nic_vm
    nic_vm=$(az network nic show -g "$RG" -n "$NIC_NAME" --query virtualMachine.id -o tsv 2>/dev/null) \
        || die "NIC $NIC_NAME not found"
    [[ -z $nic_vm ]] || die "NIC $NIC_NAME is already attached to ${nic_vm##*/}"
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
    run_az maintenance assignment create -g "$RG" -n "$MC_ASSIGNMENT_NAME" -l "$LOC" \
        --provider-name Microsoft.Compute --resource-type virtualMachines \
        --resource-name "$VM_NAME" --maintenance-configuration-id "$MC_ID" -o none
}

show_vm(){
    [[ -n $DRY_RUN ]] && return
    az vm show -d -g "$RG" -n "$VM_NAME" \
        --query "{name:name, size:hardwareProfile.vmSize, state:powerState, publicIp:publicIps, privateIp:privateIps}" \
        -o table
}

# Adds a "Host $VM_NAME" entry to SSH_CONFIG, or points an existing one at the
# VM's IP, and sets SSH_OPTS for the steps below. SSH_OPTS repeats the entry's
# settings, so the steps reach the new VM even if the config update fails.
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
        current=$(ssh_config_hostname)
        if [[ $current == "$ip" ]]; then
            echo "Host $VM_NAME is already in $SSH_CONFIG, leaving it"
            return
        fi
        # rewrite HostName in that block only; a .bak keeps the old file
        echo "Host $VM_NAME in $SSH_CONFIG points at $current, changing it to $ip..."
        cp -p "$SSH_CONFIG" "$SSH_CONFIG.bak"
        awk -v host="$VM_NAME" -v ip="$ip" '
            tolower($1) == "host" || tolower($1) == "match" {
                in_block = 0
                if (tolower($1) == "host")
                    for (i = 2; i <= NF; i++) if ($i == host) in_block = 1
            }
            in_block && tolower($1) == "hostname" { sub(/[^[:space:]]+[[:space:]]*$/, ip) }
            { print }
        ' "$SSH_CONFIG.bak" > "$SSH_CONFIG"
        [[ $(ssh_config_hostname) == "$ip" ]] \
            || echo "WARNING: couldn't update it (no HostName line?); fix Host $VM_NAME by hand" >&2
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
# Delete steps
#################################
confirm(){
    [[ -n $YES || -n $DRY_RUN ]] && return
    local answer
    read -r -p "Type the VM name to confirm: " answer
    [[ $answer == "$VM_NAME" ]] || die "confirmation didn't match, nothing deleted"
}

delete_vm(){
    echo "Deleting VM $VM_NAME..."
    run_az vm delete -g "$RG" -n "$VM_NAME" --yes
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
