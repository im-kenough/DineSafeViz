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

# --- Variables (from variables.pkrvars.hcl) ---

variable "proxmox_api_url" { type = string }
variable "proxmox_api_token_id" { type = string }
variable "proxmox_api_token_secret" {
  type      = string
  sensitive = true
}
variable "proxmox_node" { type = string }
variable "proxmox_storage" { type = string }

variable "template_ubuntu_base" { type = number }
variable "template_ubuntu_docker" { type = number }

variable "ssh_username" { type = string }
variable "build_ip_docker" { type = string }
variable "network_gateway" { type = string }

variable "cpu" { type = number }
variable "memory" { type = number }
variable "disk_size" { type = number }
variable "proxmox_bridge" { type = string }

# --- Source ---

source "proxmox-clone" "ubuntu-docker" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  clone_vm_id = var.template_ubuntu_base
  vm_id       = var.template_ubuntu_docker
  vm_name     = "ubuntu-docker"

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
    ip      = "${var.build_ip_docker}/24"
    gateway = var.network_gateway
  }

  nameserver              = var.network_gateway
  qemu_agent              = true
  cloud_init              = true
  cloud_init_storage_pool = var.proxmox_storage

  ssh_host     = var.build_ip_docker
  ssh_username = var.ssh_username
  ssh_timeout  = "15m"

  template_name        = "ubuntu-docker"
  template_description = "Ubuntu 24.04 + Docker CE, Layer 2. Built by Packer."
}

# --- Build ---

build {
  sources = ["source.proxmox-clone.ubuntu-docker"]

  provisioner "ansible" {
    playbook_file = "../ansible/playbooks/packer-docker.yml"
    user          = var.ssh_username
    use_proxy     = false
    ansible_env_vars = [
      "ANSIBLE_HOST_KEY_CHECKING=False",
      "ANSIBLE_ROLES_PATH=../ansible/roles"
    ]
  }
}
