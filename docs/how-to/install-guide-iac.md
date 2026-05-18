# IaC Install Guide — First-Time Setup

Step-by-step instructions for setting up the IaC toolchain from scratch. After
completing this guide you will have three Proxmox VM templates ready for
deployment.

## Prerequisites

### Workstation Software

Install the following on your workstation (the machine you run IaC commands
from):

1. **Packer** (>= 1.9)
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install packer
   ```
   Verify: `packer version`

2. **Terraform** (>= 1.5)
   ```bash
   sudo apt install terraform
   ```
   Verify: `terraform version`

3. **Ansible** (>= 2.15)
   ```bash
   sudo apt install ansible
   ```
   Verify: `ansible --version`

4. **Python 3 with PyYAML** (for render scripts)
   ```bash
   pip3 install pyyaml
   ```

5. **SSH key pair** (Ed25519 recommended)
   ```bash
   ssh-keygen -t ed25519 -C "iac" -f ~/.ssh/iac
   ```
   This key will be used by Packer and Ansible to SSH into VMs during builds
   and deploys.

### Proxmox Access

You need shell access (SSH or console) to the Proxmox host at `10.0.20.21`
for the initial setup steps.

## Step 1: Create Proxmox Service Accounts

SSH into the Proxmox host and create two service accounts with API tokens.

### svc-packer (for image builds)

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

**Save the token value** — it is only shown once. You will add it to the
Ansible Vault in Step 4.

### svc-terraform (for VM provisioning)

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

**Save the token value.**

## Step 2: Import the Seed Cloud Image

On the Proxmox host, download and import the Ubuntu 24.04 cloud image as
template 9000:

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
# copies the existing proxmos authorized keys into the VM config since it'll contain the IAC public key
# can be more surgical and just add your iac public key
qm set 9000 --ciuser ubuntu
qm set 9000 --sshkeys ~/.ssh/authorized_keys  # or paste your public key

# Convert to template
# Freezes the cloudinit image
qm template 9000
```
A more precise alternative

On your workstation load the IAC public key into Proxmox's tmp dir. Have the VM config reference it
```bash
cat ~/.ssh/iac.pub | ssh root@10.0.20.21 "cat > /tmp/iac.pub && qm set 9000 --sshkeys /tmp/iac.pub"
```


Verify: template 9000 should appear in the Proxmox UI under the node.

## Step 3: Configure SSH Access

Ensure your workstation's SSH public key is in the cloud-init config of
template 9000 (done in Step 2 with `--sshkeys`). Packer and Ansible use this
key to SSH into VMs during builds.

Add your `iac` public key to the template:
```bash
qm set 9000 --sshkeys ~/.ssh/iac.pub
```

Test that you can resolve the Proxmox host:
```bash
ssh root@10.0.20.21 "echo 'Proxmox SSH OK'"
```

## Step 4: Create the Ansible Vault

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

# GitHub App private key
vault_github_app_key: |
  -----BEGIN RSA PRIVATE KEY-----
  <paste your GitHub App private key here>
  -----END RSA PRIVATE KEY-----
```

Save and close. Remember your vault password — you will need it for every
`make` command.

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
