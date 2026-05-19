# infra/packer/dsv-app.pkr.hcl
#
# Layer 3: Application-ready VM with identity and GitHub deploy key.
# Clones ubuntu-docker (9101) and applies the Ansible dsv-app role.

packer {
  required_plugins {
    proxmox = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/proxmox"
    }
    ansible = {
      version = ">= 1.1.0"
      source  = "github.com/hashicorp/ansible"
    }
  }
}

# --- Variables ---

variable "proxmox_api_url" {
  type    = string
  default = "https://10.0.20.21:8006/api2/json"
}

variable "proxmox_api_token_id" {
  type = string
}

variable "proxmox_api_token_secret" {
  type      = string
  sensitive = true
}

variable "proxmox_node" {
  type = string
}

variable "clone_vm_id" {
  type    = number
  default = 9101
}

variable "template_vm_id" {
  type    = number
  default = 9102
}

variable "template_name" {
  type    = string
  default = "dsv-app"
}

variable "ssh_username" {
  type    = string
  default = "ubuntu"
}

variable "ansible_vault_password_file" {
  type    = string
  default = ""
}

# --- Source ---

source "proxmox-clone" "dsv-app" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  clone_vm_id = var.clone_vm_id
  vm_id       = var.template_vm_id
  vm_name     = var.template_name

  cores           = 2
  memory          = 2048
  scsi_controller = "virtio-scsi-pci"

  disks {
    type         = "scsi"
    storage_pool = "local-lvm"
    disk_size    = "60G"
    discard      = true
  }

  network_adapters {
    model  = "virtio"
    bridge = "vmbr0"
  }

  ipconfig {
    ip = "dhcp"
  }

  qemu_agent              = true
  cloud_init              = true
  cloud_init_storage_pool = "local-lvm"

  ssh_username = var.ssh_username
  ssh_timeout  = "15m"

  template_name        = var.template_name
  template_description = "DineSafeViz app VM — identity + GitHub deploy key, Layer 3. Built by Packer."
}

# --- Build ---

build {
  sources = ["source.proxmox-clone.dsv-app"]

  provisioner "ansible" {
    playbook_file = "../ansible/playbooks/packer-dsv-app.yml"
    user          = var.ssh_username
    # Packer's ansible provisioner defaults to routing SSH through a local proxy
    # it controls. That proxy only handles exec channels — not the SFTP
    # subsystem. Ansible's Gathering Facts step uploads AnsiballZ_setup.py via
    # SFTP, which fails silently through the proxy (empty error). Setting
    # use_proxy = false passes the real VM IP and ephemeral key directly to
    # ansible-playbook so it manages its own SSH connection (exec + SFTP).
    # Requires direct network access from the Packer host to the build VM.
    # See: docs/ref/infra/known-issues.md
    use_proxy     = false
    ansible_env_vars = [
      "ANSIBLE_HOST_KEY_CHECKING=False",
      "ANSIBLE_ROLES_PATH=../ansible/roles"
    ]
    extra_arguments = var.ansible_vault_password_file != "" ? [
      "--vault-password-file", var.ansible_vault_password_file
    ] : []
  }
}
