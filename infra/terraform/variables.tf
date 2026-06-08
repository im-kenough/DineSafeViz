# infra/terraform/variables.tf

# --- Proxmox Connection ---

variable "proxmox_api_url" {
  description = "Proxmox API endpoint"
  type        = string
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
}

# --- VM Template ---

variable "template_id" {
  description = "Proxmox VM ID of the dsv-app template to clone"
  type        = number
}

# --- VM Configuration ---

variable "vm_name" {
  description = "VM hostname"
  type        = string
}

variable "vm_id" {
  description = "Specific Proxmox VM ID"
  type        = number
}

variable "vm_cpu" {
  description = "Number of CPU cores"
  type        = number
}

variable "vm_memory" {
  description = "RAM in MB"
  type        = number
}

variable "vm_disk_size" {
  description = "Disk size in GB"
  type        = number
}

# --- Network ---

variable "vm_ip" {
  description = "Static IP address for the VM"
  type        = string
}

variable "proxmox_bridge" {
  description = "Proxmox network bridge"
  type        = string
}
