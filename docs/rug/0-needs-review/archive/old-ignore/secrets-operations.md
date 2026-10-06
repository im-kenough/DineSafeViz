# Secrets Operations

This document provides instructions for managing secrets


## Vault Operations

### View secrets

```bash
cd infra/ansible
ansible-vault view vault/secrets.yml --ask-vault-pass
```

### Edit secrets

```bash
cd infra/ansible
ansible-vault edit vault/secrets.yml --ask-vault-pass
```

### Change vault password

```bash
cd infra/ansible
ansible-vault rekey vault/secrets.yml --ask-vault-pass
```

## Rules

- **Never** commit unencrypted secrets to the repository
- **Never** hardcode passwords in `docker-compose.yml`, `.tf` files, or
  playbooks
- **Never** store `.tfvars` or `.pkrvars.hcl` files with real values in git
- **Always** use `--ask-vault-pass` (or a vault password file) when running
  Ansible or Make targets
- `.env` files exist only on the target VM, templated at deploy time