# Install guide

This document shows you how to deploy the app from scratch in a self-hosted
environment. You use a Linux workstation to connect to a self-hosted Proxmox
instance.

## Prerequisites

Before you start, make sure that you have the following:

- A Proxmox server on your LAN
- A Linux workstation

## Install steps

Complete these steps in order.

1. [Configure the workstation](1-workstation.md). Install the required
   applications, and then generate an SSH key pair for infrastructure as code
   (IaC) operations.
2. [Set up Proxmox](2-setup-proxmox.md). Create the Proxmox service accounts,
   and then assign roles and permissions to them.
3. [Create the Proxmox template](3-create-proxmox-template.md). Create a
   Proxmox VM template that cloud-init and other IaC tools customize further.
4. [Set up the application](4-setup-app.md). Create an Ansible Vault, and then
   populate it with the secret values from the previous steps.
5. [Create the VM image](5-create-vm-image.md). Create an updated VM image that
   contains all the tools and configuration that the application needs.
6. [Deploy the application](6-deploy.md). Provision a VM, deploy the
   application, and bring it up.
