# Infrastructure as code architecture

This document describes the infrastructure as code (IaC) strategy for
DineSafeViz. It explains how a layered approach provisions, configures, and
deploys the infrastructure.

## Architecture overview

DineSafeViz runs the `dsv-app` image, an Ubuntu image on a Proxmox-hosted VM.

Terraform uses the Proxmox provider to provision a Proxmox VM object. Next,
Terraform runs the DineSafeViz Ubuntu VM image. Finally, Ansible clones the app
code and deploys the Docker Compose stack.

## Image pipeline

The pipeline builds the DineSafeViz image through multiple steps.

1. Packer prepares an Ubuntu 24.04 Server image for cloud-init configuration.
2. Packer creates a base Ubuntu image with basic hardening. This image serves
   as a common image that other VM servers in the Proxmox environment reuse.
   It applies the following:
   - Minimal hardened Ubuntu 24.04 server.
   - **Security:** UFW firewall, fail2ban, disabled root and password auth.
   - **Common packages:** `curl`, `git`, `jq`, `htop`, `unattended-upgrades`.
   - **System:** NTP, timezone (America/Toronto), and DNS configuration.
3. Using `ubuntu-base`, the pipeline creates `ubuntu-docker`, which installs
   Docker and other required apps. This image is another common resource that
   other VMs reuse. It applies the following:
   - Official Docker CE repository setup.
   - Log rotation and daemon optimizations.
   - Firewall rules for Docker services.
4. Finally, the pipeline customizes the `ubuntu-docker` image to create the
   `dsv-app` image. It applies the following:
   - Hostname and static IP assignment.
   - GitHub App private keys for repository access.
   - Application directory structure.

## Variable and secret management

Two locations within the `infra/ansible/` directory centralize the
configuration.

### Variable storage

- **Non-sensitive variables:** Stored in `infra/ansible/group_vars/all.yml`.
  This file includes VM specifications (CPU, RAM), network settings, and image
  IDs.
- **Secrets:** Stored in `infra/ansible/vault/secrets.yml`. Ansible Vault
  encrypts this file, which contains API tokens, private keys, and passwords.

### Variable bridging

Terraform and Packer cannot read Ansible Vault files directly. A Python bridge
script (`infra/scripts/render-vars.py`) merges these sources into the required
formats at runtime.

## Operations

Make wraps the Terraform and Ansible orchestration. All infrastructure
operations run through the `infra/` directory.

| Command | Description |
| :--- | :--- |
| `make bake-all` | Rebuilds all three image layers from scratch. |
| `make provision-vm` | Provisions the VM using Terraform. |
| `make deploy-app` | Deploys the application using Ansible. |
| `make up` | Full end-to-end: provision VM and deploy app. |
| `make down` | Full teardown: destroy app and VM. |

## Related documents

- For secrets management, see
  [security architecture](6-security-architecture.md).
- For deployment and troubleshooting, see
  [deploy the application](../how-to/1-install/6-deploy.md).
