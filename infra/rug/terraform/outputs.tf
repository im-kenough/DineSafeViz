# infra/terraform/outputs.tf

output "vm_name" {
  description = "Name of the provisioned VM"
  value       = proxmox_virtual_environment_vm.dsv_app.name
}

output "vm_id" {
  description = "Proxmox VM ID"
  value       = proxmox_virtual_environment_vm.dsv_app.vm_id
}

output "vm_ip" {
  description = "IP address of the VM (from variable, baked into template)"
  value       = var.vm_ip
}
