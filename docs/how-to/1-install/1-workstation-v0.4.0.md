# Set up the workstation (v0.4.0)

On the workstation that issues the infrastructure as code (IaC) commands,
install the following software:

- Azure CLI
- Terraform
- Helm
- Helmfile
- kubelogin
- Ansible
- Python 3 with PyYAML

## Install the applications

### Install the Azure CLI

```bash
# Install packages
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Install Msft signing key
sudo mkdir -p /etc/apt/keyrings
curl -sLS https://packages.microsoft.com/keys/microsoft.asc |
  gpg --dearmor | sudo tee /etc/apt/keyrings/microsoft.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/microsoft.gpg

# Install Azure CLI software repo
AZ_DIST=$(lsb_release -cs)
echo "Types: deb
URIs: https://packages.microsoft.com/repos/azure-cli/
Suites: ${AZ_DIST}
Components: main
Architectures: $(dpkg --print-architecture)
Signed-by: /etc/apt/keyrings/microsoft.gpg" | sudo tee /etc/apt/sources.list.d/azure-cli.sources

# Update repository information and install the azure-cli package
sudo apt-get update
sudo apt-get install -y azure-cli

az version
```

### Install Terraform

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

### Install Ansible

```bash
sudo apt install -y ansible
ansible --version
```

### Install PyYAML

```bash
pip3 install pyyaml
```

### Install kubectl

```bash
# Update the apt package index and install packages needed to use the Kubernetes apt repository
sudo apt-get update
# apt-transport-https may be a dummy package; if so, you can skip that package
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg

# Download the public signing key for the Kubernetes package repositories.
# If the folder `/etc/apt/keyrings` does not exist, it should be created before the curl command, read the note below.
# sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.36/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
sudo chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg # allow unprivileged APT programs to read this keyring

# Add the appropriate Kubernetes apt repository. If you want to use Kubernetes version different than v1.36, replace v1.36 with the desired minor version in the command below
# This overwrites any existing configuration in /etc/apt/sources.list.d/kubernetes.list
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.36/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo chmod 644 /etc/apt/sources.list.d/kubernetes.list   # helps tools such as command-not-found to work correctly

# Update apt package index, then install kubectl
sudo apt-get update
sudo apt-get install -y kubectl

kubectl version --client
```

### Install Helm

Helm uses three main concepts:

- **Charts** are collections of files that describe a related set of Kubernetes
  resources. A chart includes templates, which generate Kubernetes manifests,
  and values, which customize the templates.
- **Releases** are instances of a chart that run in a Kubernetes cluster. A
  cluster can hold multiple releases of the same chart.
- **Repositories** are locations where you find and download charts. Public
  repositories such as Artifact Hub exist, and you can create your own private
  repositories.

```bash
HELM_BUILDKITE_APT_KEY_ID="DDF78C3E6EBB2D2CC223C95C62BA89D07698DBC6"

sudo apt-get install curl gpg apt-transport-https --yes

curl -fsSL https://packages.buildkite.com/helm-linux/helm-debian/gpgkey > "${TMPDIR:-/tmp}/helm.gpg"

# Ensure that the key ID matches to prevent a repository compromise from establishing an attacker controlled key
if [ "$(gpg --show-keys --with-colons "${TMPDIR:-/tmp}/helm.gpg" | awk -F: '$1 == "fpr" {print $10}' | head -n 1)" != "${HELM_BUILDKITE_APT_KEY_ID}" ]; then echo "ERROR: Unexpected Helm APT key ID: potential key compromise"; exit 1; fi

cat "${TMPDIR:-/tmp}/helm.gpg" | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/helm.gpg] https://packages.buildkite.com/helm-linux/helm-debian/any/ any main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list

sudo apt-get update
sudo apt-get install -y helm

helm version
```

### Install Helmfile

Helmfile lets you deploy your Kubernetes manifests, Kustomize configs, and
charts as Helm releases declaratively. For more information, see the
[Helmfile installation guide](https://github.com/helmfile/helmfile#installation).

First, install the `helm-diff` plugin.

```bash
helm plugin install https://github.com/databus23/helm-diff
```

Next, download, extract, and install the latest `helmfile` binary for Linux
Mint.

1.  Identify the latest version, and then download the compressed archive.

    ```bash
    LATEST_VERSION=$(curl -s https://api.github.com/repos/helmfile/helmfile/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    VERSION_NUM=${LATEST_VERSION#v}
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')

    curl -LO "https://github.com/helmfile/helmfile/releases/download/${LATEST_VERSION}/helmfile_${VERSION_NUM}_${OS}_${ARCH}.tar.gz"
    ```

2.  Extract the binary from the archive.

    ```bash
    tar -xvf "helmfile_${VERSION_NUM}_${OS}_${ARCH}.tar.gz" helmfile
    ```

3.  Make the binary executable, and then move it to your system PATH.

    ```bash
    chmod +x helmfile
    sudo mv helmfile /usr/local/bin/helmfile
    ```

4.  Optional: remove the downloaded archive.

    ```bash
    rm "helmfile_${VERSION_NUM}_${OS}_${ARCH}.tar.gz"
    ```

To confirm that `helmfile` is installed and available from your terminal, check
its version.

```bash
helmfile version
```

### Install kubelogin

```bash
sudo az aks install-cli

kubectl version --client

kubelogin --version
```

---

# Old

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
