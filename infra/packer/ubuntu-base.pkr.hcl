# infra/packer/ubuntu-base.pkr.hcl
#
# Layer 1: Minimal hardened Ubuntu server.
# Clones the seed cloud image (9000) and applies the Ansible base role.

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

# --- Variables (from variables.pkrvars.hcl) ---

variable "proxmox_api_url" { type = string }
variable "proxmox_api_token_id" { type = string }
variable "proxmox_api_token_secret" {
  type      = string
  sensitive = true
}
variable "proxmox_node" { type = string }
variable "proxmox_storage" { type = string }

variable "template_cloud_image" { type = number }
variable "template_ubuntu_base" { type = number }

variable "ssh_username" { type = string }
variable "build_ip_base" { type = string }
variable "network_gateway" { type = string }

variable "cpu" { type = number }
variable "memory" { type = number }
variable "disk_size" { type = number }
variable "proxmox_bridge" { type = string }

# --- Source ---

source "proxmox-clone" "ubuntu-base" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  clone_vm_id = var.template_cloud_image
  vm_id       = var.template_ubuntu_base
  vm_name     = "ubuntu-base"

  cores           = var.cpu
  memory          = var.memory
  scsi_controller = "virtio-scsi-pci"

  disks {
    type         = "scsi"
    storage_pool = var.proxmox_storage
    disk_size    = "${var.disk_size}G"
    discard      = true
  }

  network_adapters {
    model  = "virtio"
    bridge = var.proxmox_bridge
  }

  ipconfig {
    ip      = "${var.build_ip_base}/24"
    gateway = var.network_gateway
  }

  nameserver              = var.network_gateway
  qemu_agent              = true
  cloud_init              = true
  cloud_init_storage_pool = var.proxmox_storage

  ssh_host     = var.build_ip_base
  ssh_username = var.ssh_username
  ssh_timeout  = "15m"

  template_name        = "ubuntu-base"
  template_description = "Ubuntu 24.04 base image — hardened, Layer 1. Built by Packer."
}

# --- Build ---

build {
  sources = ["source.proxmox-clone.ubuntu-base"]

  provisioner "ansible" {
    playbook_file = "../ansible/playbooks/packer-base.yml"
    user          = var.ssh_username
    use_proxy     = false
    ansible_env_vars = [
      "ANSIBLE_HOST_KEY_CHECKING=False",
      "ANSIBLE_ROLES_PATH=../ansible/roles"
    ]
  }
}
