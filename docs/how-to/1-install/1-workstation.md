## Setup Workstation

On the workstation that will be issuing IAC commands, install the following software:

- packer, terraform, ansible, python 3 w/ pyYAML

```bash
# Install packer
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update
sudo apt install -y packer
packer version

```

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

```bash
sudo apt install -y ansible
ansible --version
```


```bash
pip3 install pyyaml
```

### Create SSH key

Create ssh key on your workstation that will be used for all IAC operations.

```bash
ssh-keygen -t ed25519 -C "iac" -f ~/.ssh/iac
```

### Create deploy keys

We'll create a pair of ssh keys for the deployment VM to clone down the repo

```bash
ssh-keygen -t ed25519 -f ~/.ssh/dsv-deploy-key-RO -C "DineSafeViz deploy key Read Only" -N ''
```

Cat out the public key, you'll paste this in to the Deploy Keys section later.
```bash
cat ~/.ssh/dsv-deploy-key-RO.pub
```

### Setup deploy keys

In the repo, 

- click on Settings > Deploy Keys > Add deploy key
- title = dsv-deploy-key-RO
- key = the public key
- allow write access = unchecked

Click Add Key