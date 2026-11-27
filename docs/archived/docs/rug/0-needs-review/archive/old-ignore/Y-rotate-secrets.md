# Secret rotation process

This document provides instructions to rotate secrets

# Application

# Infrastructure as Code

## Ansible vault - secrets.yaml

In the root of the repo, type in:
```bash
ansible-vault rekey infra/ansible/vault/secrets.yml
```
Enter the old password, and then the new one

## Github repo - deploy keys

## Proxmox - Terraform API token

## Proxmox - Packer API token