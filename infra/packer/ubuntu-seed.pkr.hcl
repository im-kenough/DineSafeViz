# infra/packer/ubuntu-seed.pkr.hcl
#
# Layer 0: Seed Ubuntu cloud image built from ISO.
# the raw, generic Ubuntu installer (the ISO) and turn it into a Proxmox Template that is ready for the home lab

packer {
  required_plugins {
    proxmox = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/proxmox"
    }
  }
}

# --- Variables ---

variable "proxmox_api_url" { type = string }
variable "proxmox_api_token_id" { type = string }
variable "proxmox_api_token_secret" {
  type      = string
  sensitive = true
}
variable "proxmox_node" { type = string }
variable "proxmox_storage" { type = string }
variable "proxmox_bridge" { type = string }
variable "template_cloud_image" { type = number }
variable "template_iac_public_key" { type = string }
variable "network_gateway" { type = string }
variable "cpu" { type = number }
variable "memory" { type = number }
variable "disk_size" { type = number }
variable "ssh_username" { type = string }

variable "force_download" {
  type    = bool
  default = false
}

source "proxmox-iso" "ubuntu-seed" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  vm_id   = var.template_cloud_image
  vm_name = "ubuntu-seed"

  boot_iso {
    type             = "ide"
    iso_url          = var.force_download ? "https://releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.iso?force=${timestamp()}" : "https://releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.iso"
    iso_checksum     = var.force_download ? "none" : "sha256:e907d92eeec9df64163a7e454cbc8d7755e8ddc7ed42f99dbc80c40f1a138433"
    iso_download_pve = true
    unmount          = true
    iso_storage_pool = "local"
  }

  cores  = var.cpu
  memory = var.memory

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

  boot_command = [
    "<esc><wait>",
    "e<wait>",
    "<down><down><down><end>",
    " autoinstall ds=nocloud-net;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/ ",
    "<f10>"
  ]

  boot_wait      = "5s"
  
  http_content = {
    "/user-data" = templatefile("http/user-data.pkrtpl.hcl", { ssh_key = var.template_iac_public_key })
    "/meta-data" = ""
  }

  ssh_username = var.ssh_username
  ssh_password = "ubuntu"
  ssh_timeout  = "20m"

  # Cloud-Init configuration for the resulting template
  cloud_init              = true
  cloud_init_storage_pool = var.proxmox_storage

  template_name        = "ubuntu-seed"
  template_description = "Ubuntu 24.04 Seed Image (Layer 0). Built by Packer."
}

build {
  sources = ["source.proxmox-iso.ubuntu-seed"]

  provisioner "shell" {
    inline = [
      "while [ ! -f /var/lib/cloud/instance/boot-finished ]; do echo 'Waiting for cloud-init...'; sleep 1; done",
      "sudo cloud-init clean --logs --seed",
      "sudo truncate -s 0 /etc/machine-id",
      "sudo apt-get clean"
    ]
  }
}
