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
  type = string
}

variable "proxmox_api_token_id" {
  type = string
}

variable "proxmox_api_token_secret" {
  type      = string
  sensitive = true
}

variable "proxmox_node" {
  type    = string
  default = "pve"
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

# --- Source ---

source "proxmox-clone" "ubuntu-base" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  clone_vm_id = var.clone_vm_id
  vm_id       = var.template_vm_id
  vm_name     = var.template_name

  cores  = 2
  memory = 2048

  network_adapters {
    bridge = "vmbr0"
  }

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
    ansible_env_vars = [
      "ANSIBLE_HOST_KEY_CHECKING=False"
    ]
  }
}
