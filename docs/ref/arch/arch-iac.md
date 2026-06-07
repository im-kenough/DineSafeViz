# Infrastructure as Code Architecture

This document describes the Infrastructure as Code (IaC) strategy for
DineSafeViz. It explains how infrastructure is provisioned, configured, and
deployed using a layered approach.

## Architecture Overview

Dinesafeviz runs the "dsv-app" image, a ubuntu image on a Proxmox hosted VM.

Terraform uses the Proxmox provider to provision a Proxmox VM object. Next Terraform runs the DineSafeViz ubuntu VM image. Finally, Ansible clones the app code and deploys the Docker Compose stack.

# Image Pipeline

THe DineSafeViz image is created through multiple steps.

1. A Ubuntu 24.04 Server image is prepared for cloud-init configuration
2. A base ubuntu image with basic hardening is created. This serves as common image to be re-used for other VM servers in the proxmox environment. Applies:
     - Minimal hardened Ubuntu 24.04 server.
     - **Security**: UFW firewall, fail2ban, disabled root/password auth.
     - **Common Packages**: `curl`, `git`, `jq`, `htop`, `unattended-upgrades`.
     - **System**: NTP, Timezone (America/Toronto), DNS configuration.
3. Using `ubuntu-base`, `ubuntu-docker` is created which installs ubuntu and other required apps. This is another common resource that can be re-used for other. Applies:
   - Official Docker CE repository setup.
   - Log rotation and daemon optimizations.
   - Firewall rules for Docker services.

4. Finally, the `ubuntu-docker` image is customized to create the `dvs-app` image. Applies:
   - Hostname and static IP assignment.
   - GitHub App private keys for repository access.
   - Application directory structure.



## Variable and Secret Management

Configuration is centralized in two locations within the `infra/ansible/`
directory.

### Variable Storage

- **Non-sensitive variables**: Stored in `infra/ansible/group_vars/all.yml`. This
  includes VM specifications (CPU, RAM), network settings, and image IDs.
- **Secrets**: Stored in `infra/ansible/vault/secrets.yml`. This file is
  encrypted with Ansible Vault and contains API tokens, private keys, and
  passwords.

### Variable Bridging

Because Terraform and Packer cannot natively read Ansible Vault files, a Python
bridge script (`infra/scripts/render-vars.py`) merges these sources into the
required formats at runtime.

## Operations

Make is used as a wrapper for Terraform and Ansible orchestration.

All infrastructure operations are managed through the `infra/` directory.

| Command | Description |
| :--- | :--- |
| `make bake-all` | Rebuilds all three image layers from scratch. |
| `make provision-vm` | Provisions the VM using Terraform. |
| `make deploy-app` | Deploys the application using Ansible. |
| `make up` | Full end-to-end: provision VM and deploy app. |
| `make down` | Full teardown: destroy app and VM. |

## Next Steps

- Review the [Secrets Management](secrets-mgt.md) guide for details on Vault
  usage.
- See the [Operations Guide](../../ops/index.md) for troubleshooting and
  maintenance procedures.
