# Secret rotation process

This document provides instructions on how to rotate secrets.

## Application

## Infrastructure as Code

## Ansible vault - secrets.yaml

In the root of the repo, type in:
```bash
ansible-vault rekey infra/ansible/vault/secrets.yml
```
Enter the old password, and then the new one

## Github repo - deploy keys

## Proxmox - Terraform API token

## Proxmox - Packer API token

## Appendix

### Ansible Vault Operations

#### View secrets

```bash
cd infra/ansible
ansible-vault view vault/secrets.yml --ask-vault-pass
```

#### Edit secrets

```bash
cd infra/ansible
ansible-vault edit vault/secrets.yml --ask-vault-pass
```

#### Change vault password

```bash
cd infra/ansible
ansible-vault rekey vault/secrets.yml --ask-vault-pass
```