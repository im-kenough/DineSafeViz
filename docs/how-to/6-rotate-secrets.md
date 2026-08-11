# Rotate secrets

This guide shows you how to rotate the secrets that DineSafeViz uses. To rotate
a secret, you change its value.

## Application secrets

### DSV_DB_PASSWORD

1. Run `ansible-vault edit` to decrypt the `secrets.yml` file.
2. Set a new value for `DSV_DB_PASSWORD`.

### DSV_ANALYTICS_ADMIN_PASSWORD

1. Run `ansible-vault edit` to decrypt the `secrets.yml` file.
2. Set a new value for `DSV_ANALYTICS_ADMIN_PASSWORD`.

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
