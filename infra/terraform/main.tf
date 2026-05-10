# infra/terraform/main.tf

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = ">= 0.66.0"
    }
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_api_url
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token_secret}"
  insecure  = true
}

resource "proxmox_virtual_environment_vm" "dsv_app" {
  name      = var.vm_name
  node_name = var.proxmox_node

  clone {
    vm_id = var.template_id
  }

  cpu {
    cores = var.vm_cpu
  }

  memory {
    dedicated = var.vm_memory
  }

  agent {
    enabled = true
  }

  disk {
    datastore_id = var.proxmox_storage
    interface    = "scsi0"
    size         = var.vm_disk_size
  }

  network_device {
    bridge = var.network_bridge
  }

  # IP, hostname, and SSH keys are baked into the template (Layer 3).
  # No cloud-init initialization needed.

  lifecycle {
    ignore_changes = [initialization]
  }
}
