# IaC Install Guide — First-Time Setup

Step-by-step instructions for setting up the IaC toolchain from scratch. After
completing this guide you will have three Proxmox VM templates ready for
deployment.

# Setting up IAC in Proxmox

Instructions for setting up tool chain to create VMs and provision them

## Setup Workstation

On the workstation that will be issuing IAC commands, install the following software:

- packer, terraform, ansible, python 3 w/ pyYAML

```bash
# Install packer
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update
sudo apt install -y packer
packer version

```

```bash
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common

wget -O- https://apt.releases.hashicorp.com/gpg | \
gpg --dearmor | \
sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null

gpg --no-default-keyring \
--keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg \
--fingerprint

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update
sudo apt-get install -y terraform

terraform -v
```

```bash
sudo apt install -y ansible
ansible --version
```


```bash
pip3 install pyyaml
```

### Create SSH key

Create ssh key on your workstation that will be used for all IAC operations.

```bash
ssh-keygen -t ed25519 -C "iac" -f ~/.ssh/iac
```

## Setup Proxmox

### Create Proxmox service accounts

- SSH into proxmox with root credentials

#### Create `svc-packer`

Create a paker service account `svc-packer` for image builds


```bash
# Create user
pveum user add svc-packer@pve --comment "Packer image build service account"

# Create role with required permissions
pveum role add Packer -privs "VM.Allocate VM.Clone VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network VM.Config.Options VM.Config.Cloudinit VM.Audit VM.Console VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit Sys.Modify SDN.Use"

# Assign role to user on root path
pveum aclmod / -user svc-packer@pve -role Packer

# Create API token (save the output!)
pveum user token add svc-packer@pve packer --privsep 0
```

**Save the token value** — it is only shown once.

#### Create `svc-terraform`

Create a terraform service account `svc-terraform` for vm provisioning

```bash
# Create user
pveum user add svc-terraform@pve --comment "Terraform provisioning service account"

# Create role with required permissions
pveum role add Terraform -privs "VM.Allocate VM.Clone VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network VM.Config.Options VM.Config.Cloudinit VM.Audit VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit SDN.Use"

# Assign role to user on root path
pveum aclmod / -user svc-terraform@pve -role Terraform

# Create API token (save the output!)
pveum user token add svc-terraform@pve terraform --privsep 0
```

Save the token you'll only see it once.

### Create the proxmox template

Import the proxmox image.
Create a VM config, convert to a template
```bash
# Download cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img \
  -O /var/lib/vz/template/iso/ubuntu-24.04-cloud.img

# Create VM shell
qm create 9000 --name ubuntu-2404-cloud --memory 4096 --cores 4 \
  --net0 virtio,bridge=vmbr0

# Import disk
qm importdisk 9000 /var/lib/vz/template/iso/ubuntu-24.04-cloud.img local-lvm

# Configure disk and boot
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --boot c --bootdisk scsi0

# Add cloud-init drive and serial console
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --serial0 socket --vga serial0

# Enable QEMU guest agent
qm set 9000 --agent enabled=1

# Set cloud-init defaults (SSH key for Packer to connect)
qm set 9000 --ciuser ubuntu
```

On your workstation, upload your IAC public key into Proxmox's temp dir.
Then tell the VM to import the key from that dir.
Once converted to a template, the image is frozen and persists the authorized public key

```bash
cat ~/.ssh/iac.pub | ssh root@10.0.20.21 "cat > /tmp/iac.pub && qm set 9000 --sshkeys /tmp/iac.pub"
```
## Setup Github repo

### Create deploy keys

We'll create a pair of ssh keys for the deployment VM to clone down the repo

```bash
ssh-keygen -t ed25519 -f ~/.ssh/dsv-deploy-key-RO -C "DineSafeViz deploy key Read Only" -N ''
```

Cat out the public key, you'll paste this in to the Deploy Keys section later.
```bash
cat ~/.ssh/dsv-deploy-key-RO.pub
```

### Setup deploy keys

In the repo, 

- click on Settings > Deploy Keys > Add deploy key
- title = dsv-deploy-key-RO
- key = the public key
- allow write access = unchecked

Click Add Key

### Create the Ansible vault

From the repo root:

```bash
cd infra/ansible
ansible-vault create vault/secrets.yml
```

When the editor opens, enter all secrets (use the real values from Steps 1-2):

```yaml
# Proxmox API tokens
vault_proxmox_api_token_id: "svc-terraform@pve!terraform"
vault_proxmox_api_token_secret: "<token from Step 1>"
vault_packer_api_token_id: "svc-packer@pve!packer"
vault_packer_api_token_secret: "<token from Step 1>"

# PostgreSQL credentials
vault_db_user: "dinesafe"
vault_db_password: "<choose a strong password>"
vault_db_name: "dinesafe"

# Grafana credentials
vault_analytics_admin_user: "admin"
vault_analytics_admin_password: "<choose a strong password>"

# GitHub deploy key private key
vault_github_deploy_keys: |
  -----BEGIN RSA PRIVATE KEY-----
  <paste your GitHub App private key here>
  -----END RSA PRIVATE KEY-----
```

## Step 5: Build Image Layers

Build all three layers in order. Each command will prompt for your vault
password.

```bash
cd infra

# Layer 1: ubuntu-base (template 9100)
make bake-base

# Layer 2: ubuntu-docker (template 9101)
make bake-docker

# Layer 3: dsv-app (template 9102)
make bake-dsv-app
```

Or build all at once:
```bash
make bake-all
```

Each build takes approximately 5-15 minutes depending on network speed and
Proxmox host performance.

## Step 6: Verify

Check that all three templates exist in the Proxmox UI:

| Template ID | Name | Description |
|-------------|------|-------------|
| 9000 | ubuntu-2404-cloud | Upstream cloud image (seed) |
| 9100 | ubuntu-base | Hardened Ubuntu (Layer 1) |
| 9101 | ubuntu-docker | Ubuntu + Docker CE (Layer 2) |
| 9102 | dsv-app | App VM identity + GitHub key (Layer 3) |

You can also verify from the command line:
```bash
ssh root@10.0.20.21 "qm list" | grep -E "9[01][0-9]{2}"
```

## Next Steps

The image pipeline is complete. To provision a VM and deploy the app, see the
[IaC Deploy Guide](deploy-guide-iac.md).
