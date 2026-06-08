# Secret rotation process

This document provides instructions on how to rotate secrets (change the password).

## Application

### DSV_DB_PASSWORD

- use `ansible-vault edit` to decrypt secrets.yaml
- create a new value for DSV_DB_PASSWORD


### DSV_ANALYTICS_ADMIN_PASSWORD

- use `ansible-vault edit` to decrypt secrets.yaml
- create a new value for DSV_ANALYTICS_ADMIN_PASSWORD

## Infrastructure as Code

### Ansible vault - secrets.yaml

In the root of the repo, type in:
```bash
ansible-vault rekey infra/ansible/vault/secrets.yml
```
Enter the old password, and then the new one

### Proxmox - IAC ssh key

On your workstation, create an ssh key

```bash
ssh-keygen -t ed25519 -C "iac" -f ~/.ssh/iac
```

### Proxmox - Terraform API token

- Login to Proxmox
- delete the service account
- recreate the service account, re-apply the role to the account

### Proxmox - Packer API token

- Login to Proxmox
- delete the service account
- recreate the service account, re-apply the role to the account

### Github repo - deploy keys

#### Re-create deploy keys

We'll create a pair of ssh keys for the deployment VM to clone down the repo

```bash
ssh-keygen -t ed25519 -f ~/.ssh/dsv-deploy-key-RO -C "DineSafeViz deploy key Read Only" -N ''
```

Cat out the public key, you'll paste this in to the Deploy Keys section later.
```bash
cat ~/.ssh/dsv-deploy-key-RO.pub
```

#### Replace deploy keys

In the repo, 

- click on Settings > Deploy Keys > Add deploy key
- title = dsv-deploy-key-RO
- key = the public key
- allow write access = unchecked

Click Add Key

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