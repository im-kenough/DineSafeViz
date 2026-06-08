# Install Guide

This document provides instructions for deploying this app from scratch in a self hosted environment.

We will use a linux workstation to connect to a self hosted Proxmox instance

## Prerequisites

You have:
- a Proxmox server setup on your LAN
- a Linux workstation

## Install Instructions

### 1 Configure Workstation

- [Configuration Workstation](docs/how-to/install/1-workstation.md). 

  - We need to install the required applications and generate a SSH keypair to use for Infrastructure as Code (IAC) operations

### 2 Setup Proxmox

- [Setup proxmox](docs/how-to/install/2-setup-proxmox.md)
  - Create proxmox service accounts
  - assign Proxmox roles and permissions to service accounts

### 3 Create Proxmox Template

- [Create Proxmox Template](docs/how-to/install/3-create-proxmox-template.md)
  - Creates a Proxmox VM template that can be further customized by cloudinit and other IAC tools

### 4 Setup application

- [Setup application](docs/how-to/install/4-setup-app.md)
  - Create an Ansible vault and populate it with the secret values created in previous steps

### 5 Create image

- [Create VM image](docs/how-to/install/5-create-vm-image.md)
  - creates an updated VM image containing all required tools and configurations to run the application

### 6 Deploy

- [Deploy application](docs/how-to/install/6-deploy.md)
  - Automatically provisions a VM and deploys the application and brings up the application.