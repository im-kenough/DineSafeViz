variable "az_location" {
  description = "Azure location for resources"
  type        = string
  default     = "canadacentral"
}

variable "tag_team_name" {
  description = "Tag for team name"
  type        = string
  default     = "DevOps"
}

variable "tag_project_name" {
  description = "Tag for project name"
  type        = string
  default     = "DineSafeViz"
}

variable "environment" {
  description = "environment type"
  type        = string
  default     = "stg"
}

variable "code_name" {
  description = "code name for the project"
  type        = string
  default     = "dsv"
}