# infra/terraform/variables.tf

# --- Proxmox Connection (secrets — from terraform.tfvars) ---

variable "proxmox_api_url" {
  description = "Proxmox API endpoint"
  type        = string
  default     = "https://10.0.20.21:8006"
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID (e.g., svc-terraform@pve!terraform)"
  type        = string
}

variable "proxmox_api_token_secret" {
  description = "Proxmox API token secret"
  type        = string
  sensitive   = true
}

# --- Proxmox Host ---

variable "proxmox_node" {
  description = "Proxmox node name as shown in the UI"
  type        = string
}

variable "proxmox_storage" {
  description = "Storage backend for VM disks"
  type        = string
  default     = "local-lvm"
}

# --- VM Template ---

variable "template_id" {
  description = "Proxmox VM ID of the dsv-app template to clone"
  type        = number
  default     = 9102
}

# --- VM Configuration ---

variable "vm_name" {
  description = "VM hostname"
  type        = string
  default     = "yyz-app-dsv01"
}

variable "vm_cpu" {
  description = "Number of CPU cores"
  type        = number
  default     = 2
}

variable "vm_memory" {
  description = "RAM in MB"
  type        = number
  default     = 4096
}

variable "vm_disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 60
}

# --- Network ---

variable "vm_ip" {
  description = "Static IP address for the VM"
  type        = string
  default     = "10.0.20.80"
}

variable "network_bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr0"
}
