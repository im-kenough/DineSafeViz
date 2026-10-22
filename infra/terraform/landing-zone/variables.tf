variable "env" {
  description = "Environment: stg or prod."
  type        = string

  validation {
    condition     = contains(["stg", "prod"], var.env)
    error_message = "env must be stg or prod."
  }
}

variable "subscription_id" {
  description = "The environment's subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "location" {
  description = "Azure region for new resources."
  type        = string
}

variable "lock_iac_rg" {
  description = "CanNotDelete lock on rg-dsv-<env>01-iac. Turn off only to delete something in it."
  type        = bool
  default     = true
}

variable "lock_core_rg" {
  description = "CanNotDelete lock on rg-dsv-<env>01. Off until the VMs move to -compute (sub-project 3)."
  type        = bool
  default     = false
}

variable "budget_amount" {
  description = "Monthly budget in the billing currency (CAD)."
  type        = number
  default     = 40
}

variable "budget_contact_emails" {
  description = "Budget alert recipients. Set in the gitignored landing-zone.secret.tfvars."
  type        = list(string)
  sensitive   = true
}
