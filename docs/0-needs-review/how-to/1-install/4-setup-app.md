# Set up the application

## Create the Ansible Vault

From the repository root, run the following commands.

```bash
cd infra/ansible
ansible-vault create vault/secrets.yml
```

When the editor opens, enter the following secrets. Use the real values from
steps 1 and 2.

```yaml
# Proxmox API token secrets (the token IDs are in group_vars/all.yml)
vault_proxmox_api_token_secret: "REPLACE_WITH_TERRAFORM_TOKEN_SECRET"
vault_packer_api_token_secret: "REPLACE_WITH_PACKER_TOKEN_SECRET"

# PostgreSQL passwords
vault_db_password: "REPLACE_WITH_DB_SUPERUSER_PASSWORD"
vault_db_app_password: "REPLACE_WITH_DB_APP_PASSWORD"

# Grafana admin password
vault_analytics_admin_password: "REPLACE_WITH_GRAFANA_ADMIN_PASSWORD"

# GitHub deploy key (private key)
vault_github_deploy_keys: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  REPLACE_WITH_DEPLOY_KEY_PRIVATE_KEY
  -----END OPENSSH PRIVATE KEY-----
```

The vault holds secrets only. Non-secret identifiers — the Proxmox token IDs,
database usernames, database name, and Grafana admin username — are set in
`infra/ansible/group_vars/all.yml`. For the full inventory and how each value
is used, see [security architecture](../../explanation/6-security-architecture.md).
