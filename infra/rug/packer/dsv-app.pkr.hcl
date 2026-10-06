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

# --- Variables (from variables.pkrvars.hcl) ---

variable "proxmox_api_url" { type = string }
variable "proxmox_api_token_id" { type = string }
variable "proxmox_api_token_secret" {
  type      = string
  sensitive = true
}
variable "proxmox_node" { type = string }
variable "proxmox_storage" { type = string }
variable "proxmox_bridge" { type = string }

variable "template_ubuntu_docker" { type = number }
variable "template_dsv_app" { type = number }

variable "ssh_username" { type = string }
variable "build_ip_app" { type = string }
variable "network_gateway" { type = string }

variable "cpu" { type = number }
variable "memory" { type = number }
variable "disk_size" { type = number }

variable "vault_github_deploy_keys" {
  type      = string
  sensitive = true
}

# --- Source ---

source "proxmox-clone" "dsv-app" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  clone_vm_id = var.template_ubuntu_docker
  vm_id       = var.template_dsv_app
  vm_name     = "dsv-app"

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
    ip      = "${var.build_ip_app}/24"
    gateway = var.network_gateway
  }

  nameserver              = var.network_gateway
  qemu_agent              = true
  cloud_init              = true
  cloud_init_storage_pool = var.proxmox_storage

  ssh_host     = var.build_ip_app
  ssh_username = var.ssh_username
  ssh_timeout  = "15m"

  template_name        = "dsv-app"
  template_description = "DineSafeViz app VM — identity + GitHub deploy key, Layer 3. Built by Packer."
}

# --- Build ---

build {
  sources = ["source.proxmox-clone.dsv-app"]

  provisioner "ansible" {
    playbook_file = "../ansible/playbooks/packer-dsv-app.yml"
    user          = var.ssh_username
    use_proxy     = false
    ansible_env_vars = [
      "ANSIBLE_HOST_KEY_CHECKING=False",
      "ANSIBLE_ROLES_PATH=../ansible/roles"
    ]
    extra_arguments = [
      "-e", "vault_github_deploy_keys=${var.vault_github_deploy_keys}"
    ]
  }
}
