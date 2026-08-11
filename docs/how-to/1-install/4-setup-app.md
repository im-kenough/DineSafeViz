# Set up the application

## Create the Ansible Vault

From the repository root, run the following commands.

```bash
cd infra/ansible
ansible-vault create vault/secrets.yml
```

When the editor opens, enter all the secrets. Use the real values from steps 1
and 2.

```yaml
# Proxmox Configuration
vault_proxmox_node: "yyz-hyp01"

## Proxmox API tokens
vault_proxmox_api_token_id: "svc-terraform@pve!terraform"
vault_proxmox_api_token_secret: "aaaaaaaaaaaaaaaaaaaaaaa"
vault_packer_api_token_id: "svc-packer@pve!packer"
vault_packer_api_token_secret: "bbbbbbbbbbbbbbbbbbbb"

# PostgreSQL credentials
vault_db_user: "dinesafe"
vault_db_password: "ccccccccccccc"
vault_db_name: "dinesafe"

# Grafana credentials
vault_analytics_admin_user: "admin"
vault_analytics_admin_password: "ddddddddddd"

# github deploy key
vault_github_deploy_keys: |
  -----BEGIN RSA PRIVATE KEY-----
  eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
  -----END RSA PRIVATE KEY-----
```
