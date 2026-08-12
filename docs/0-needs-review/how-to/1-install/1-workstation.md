# Set up the workstation

On the workstation that issues the infrastructure as code (IaC) commands,
install the following software:

- Packer
- Terraform
- Ansible
- Python 3 with PyYAML

## Install Packer

```bash
# Install packer
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update
sudo apt install -y packer
packer version
```

## Install Terraform

```bash
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common

wget -O- https://apt.releases.hashicorp.com/gpg | \
gpg --dearmor | \
sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null

gpg --no-default-keyring \
--keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg \
--fingerprint

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update
sudo apt-get install -y terraform

terraform -v
```

## Install Ansible

```bash
sudo apt install -y ansible
ansible --version
```

## Install PyYAML

```bash
pip3 install pyyaml
```

## Create the SSH key

Create an SSH key on your workstation. You use this key for all IaC operations.

```bash
ssh-keygen -t ed25519 -C "iac" -f ~/.ssh/iac
```

## Create the deploy keys

Create a pair of SSH keys for the deployment VM to clone the repository.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/dsv-deploy-key-RO -C "DineSafeViz deploy key Read Only" -N ''
```

Display the public key. You paste this value into the **Deploy keys** section
in the next step.

```bash
cat ~/.ssh/dsv-deploy-key-RO.pub
```

## Set up the deploy keys

In the repository, follow these steps.

1. Go to **Settings** > **Deploy keys** > **Add deploy key**.
2. In **Title**, enter `dsv-deploy-key-RO`.
3. In **Key**, enter the public key.
4. Clear **Allow write access**.
5. Click **Add key**.
