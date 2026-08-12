# Rotate secrets

This guide shows you how to rotate the secrets that DineSafeViz uses. To rotate
a secret, you change its value.

## Application secrets

The application passwords live in the Ansible Vault as `vault_*` keys. Ansible
renders them into the `.env` file on the VM at deploy time. For the full
inventory, see [security architecture](../ref/arch/arch-security.md).

### PostgreSQL superuser password

1. Run `ansible-vault edit` to open the `secrets.yml` file.
2. Set a new value for `vault_db_password`.

### PostgreSQL app-role password

1. Run `ansible-vault edit` to open the `secrets.yml` file.
2. Set a new value for `vault_db_app_password`.

### Grafana admin password

1. Run `ansible-vault edit` to open the `secrets.yml` file.
2. Set a new value for `vault_analytics_admin_password`.

## Infrastructure secrets

### Ansible Vault password

From the root of the repository, run the following command.

```bash
ansible-vault rekey infra/ansible/vault/secrets.yml
```

Enter the old password, and then enter the new password.

### Proxmox IaC SSH key

On your workstation, create an SSH key.

```bash
ssh-keygen -t ed25519 -C "iac" -f ~/.ssh/iac
```

### Proxmox Terraform API token

1. Log in to Proxmox.
2. Delete the service account.
3. Recreate the service account, and then reapply the role to the account.

### Proxmox Packer API token

1. Log in to Proxmox.
2. Delete the service account.
3. Recreate the service account, and then reapply the role to the account.

### GitHub deploy keys

#### Recreate the deploy keys

Create a pair of SSH keys for the deployment VM to clone the repository.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/dsv-deploy-key-RO -C "DineSafeViz deploy key Read Only" -N ''
```

Display the public key. You paste this value into the **Deploy keys** section
in the next step.

```bash
cat ~/.ssh/dsv-deploy-key-RO.pub
```

#### Replace the deploy keys

In the repository, follow these steps.

1. Go to **Settings** > **Deploy keys** > **Add deploy key**.
2. In **Title**, enter `dsv-deploy-key-RO`.
3. In **Key**, enter the public key.
4. Clear **Allow write access**.
5. Click **Add key**.

## Appendix: Ansible Vault operations

### View the secrets

```bash
cd infra/ansible
ansible-vault view vault/secrets.yml --ask-vault-pass
```

### Edit the secrets

```bash
cd infra/ansible
ansible-vault edit vault/secrets.yml --ask-vault-pass
```

### Change the Vault password

```bash
cd infra/ansible
ansible-vault rekey vault/secrets.yml --ask-vault-pass
```
