terraform {
  required_version = "~> 1.16"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.10"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.10"
    }
  }

  # Settings come from envs/<env>/landing-zone.backend.hcl. During the first
  # apply, `make bootstrap` overrides this with local state.
  backend "azurerm" {}
}
