# infra/packer/ubuntu-docker.pkr.hcl
#
# Layer 2: Docker-ready VM.
# Clones ubuntu-base (9100) and applies the Ansible docker role.

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
  default = 9100
}

variable "template_vm_id" {
  type    = number
  default = 9101
}

variable "template_name" {
  type    = string
  default = "ubuntu-docker"
}

variable "ssh_username" {
  type    = string
  default = "ubuntu"
}

# --- Source ---

source "proxmox-clone" "ubuntu-docker" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  clone_vm_id = var.clone_vm_id
  vm_id       = var.template_vm_id
  vm_name     = var.template_name

  cores           = 4
  memory          = 6144
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
  template_description = "Ubuntu 24.04 + Docker CE, Layer 2. Built by Packer."
}

# --- Build ---

build {
  sources = ["source.proxmox-clone.ubuntu-docker"]

  provisioner "ansible" {
    playbook_file = "../ansible/playbooks/packer-docker.yml"
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
  }
}
