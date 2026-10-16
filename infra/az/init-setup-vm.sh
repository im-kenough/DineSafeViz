#!/bin/bash
set -euo pipefail
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/lib.sh"


##########################
# Install applications
install_docker(){
    echo ""
    echo "Installing Docker..." 
    # Add Docker's official GPG key:
    sudo apt install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository to Apt sources:
    sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

    sudo apt update

    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    echo "Configuring docker to start on boot with systemd"
    sudo systemctl enable docker.service containerd.service

    #make docker nonroot
    # docker-ce creates the docker group; -f makes this a no-op if it exists.
    # Membership applies on next login, so use sg for docker calls in this run.
    sudo groupadd -f docker
    sudo usermod -aG docker "$USER"
    sg docker -c "docker run hello-world"
    echo "Docker installed"

}

install_applications(){
    echo ""
    echo "Performing initial updates"
    sudo apt update && sudo apt full-upgrade -y

    install_docker

    echo ""
    echo "Installing other required apps"
    sudo apt install -y jq

    sudo apt autoremove -y && sudo apt clean
}
#########################

add_swap_file(){
    echo ""
    echo "Adding swap file"
    # Skip creation if the swap file is already active so reruns don't fail.
    if swapon --show=NAME --noheadings | grep -qx /swapfile; then
        echo "/swapfile already active, skipping creation"
    else
        sudo fallocate -l 2G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile && sudo swapon /swapfile
    fi
    grep -q '^/swapfile ' /etc/fstab \
        || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-dsv-swap.conf
    sudo sysctl --system >/dev/null
    swapon --show
}

verify_az_kv_access(){
    local token
    token=$(imds_token https%3A%2F%2Fvault.azure.net)
    curl -s -H "Authorization: Bearer $token" \
    "https://kv-dsv-stg01.vault.azure.net/secrets?api-version=7.4" \
    | jq -r '.value[].id | split("/") | last'
}

########################
# Block containers from the instance metadata service

block_imds_from_containers(){
    echo ""
    echo "Block containers from reaching IMDS service"
    sudo install -m 644 deploy/systemd/dsv-imds-block.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now dsv-imds-block.service
    sudo iptables -S DOCKER-USER | grep -E '169.254.169.254|168.63.129.16'    
}

verify_block_imds(){
    echo ""
    echo "Verify containers are blocked from IMDS service"
    sudo docker run --rm curlimages/curl -s -m 3 -H Metadata:true \
      "http://169.254.169.254/metadata/instance?api-version=2021-02-01" \
      && echo "NOT BLOCKED" || echo "Blocked"
}

verify_host_access_to_imds(){
    echo ""
    echo "Verify host vm still has IMDS access"
    curl -s -H Metadata:true \
      "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net" \
      | jq -r '.expires_in'    
}

secure_imds(){
    block_imds_from_containers
    verify_block_imds
    verify_host_access_to_imds
}

########################
# Application configuration - Setup data refresh timer

setup_data_refresh_timer(){
    for f in dsv-pipeline.service dsv-pipeline.timer; do
        sed -e "s|@ADMIN_USER@|$USER|" -e "s|@REPO_DIR@|$PWD|" -e "s|@ENV@|stg|" \
        "deploy/systemd/$f" | sudo tee "/etc/systemd/system/$f" >/dev/null
    done
    sudo systemctl daemon-reload
    sudo systemctl enable --now dsv-pipeline.timer    
}

#####################
# Main function

main(){
    install_applications
    add_swap_file
    
    secure_imds
    verify_az_kv_access
    setup_data_refresh_timer
    echo "Done."
}

main "$@"