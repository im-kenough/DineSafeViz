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
  default = 9000
}

variable "template_vm_id" {
  type    = number
  default = 9100
}

variable "template_name" {
  type    = string
  default = "ubuntu-base"
}

variable "ssh_username" {
  type    = string
  default = "ubuntu"
}

variable "build_ip" {
  type        = string
  default     = "10.0.20.200"
  description = "Temporary static IP for the Layer 1 build VM. Must be outside the DHCP range."
}

variable "network_gateway" {
  type    = string
  default = "10.0.20.1"
}

# --- Source ---

# Layer 1 uses a static IP instead of DHCP because the seed cloud image
# (9000) has no qemu-guest-agent — Packer can't discover a DHCP address
# without the agent. The Ansible base role installs the agent, so Layers
# 2+ can use qemu_agent = true with DHCP.

source "proxmox-clone" "ubuntu-base" {
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
    ip      = "${var.build_ip}/24"
    gateway = var.network_gateway
  }

  nameserver = var.network_gateway

  ssh_host     = var.build_ip
  ssh_username = var.ssh_username
  ssh_timeout  = "15m"

  template_name        = var.template_name
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
