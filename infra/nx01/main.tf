# Configure AZ provider
terraform {
  # Set Azure Resource Manager provider source and version to be used
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>5.15.0"
    }
  }
  required_version = ">= 1.1.0"
}

# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {}
}

######################################

resource "azurerm_resource_group" "rg" {
  name     = "rg-dsv-stg02-test01"
  location = var.az_location
}

# Create a virtual network
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-dsv-stg02-test01"
  address_space       = ["192.168.0.0/16"]
  location            = var.az_location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    Team        = var.tag_team_name
    Project     = var.tag_project_name
    Environment = var.environment
    code_name   = var.code_name
  }
}
