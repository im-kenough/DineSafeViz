# Installation guide

Complete instructions for installing and running DineSafeViz on a fresh Ubuntu VM.

## System requirements

DineSafeViz is a dockerized application, so you'll need Docker and Docker Compose installed on your system. The application has been tested on Ubuntu 20.04 LTS and later.

**Hardware:**
- CPU: 2+ cores (recommended)
- RAM: 2 GB minimum (4 GB recommended for better performance)
- Storage: 20 GB free disk space (for Docker images and database)

**Operating system:**
- Ubuntu 20.04 LTS or later
- Other Linux distributions with Docker support are compatible

## Step 1: Install required packages

Install system utilities needed for the setup process:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git nano curl
```

## Step 2: Install Docker and Docker Compose
```bash
# Add Docker's official GPG key:
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update

sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl start docker
sudo docker run hello-world

sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
docker run hello-world
```

## Step 3: Generate and add SSH key to GitHub

To access the repository, you'll need to set up an SSH key and add it to GitHub.

```bash
ssh-keygen -t ed25519 -C "yyz-app01-test"
```

When prompted for a location, press Enter to use the default (`~/.ssh/id_ed25519`).

Display your public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output. We'll paste the public key into the repo as a deploy key.

- **GitHub:** Go to [https://github.com/im-kenough/DineSafeViz/settings/keys/new](https://github.com/im-kenough/DineSafeViz/settings/keys/new), click "Add new SSH key,"
- Title: "yyz-app01-test"
- Key: the value of your public key
- Click add key

Test your SSH connection:

```bash
ssh -T git@github.com
```

You should see a message confirming successful authentication.

## Step 4: Clone the repository

Create a working directory and clone the DineSafeViz repository:

```bash
mkdir -p ~/app
cd ~/app
git clone git@github.com:im-kenough/DineSafeViz.git
cd DineSafeViz
```

Verify the clone was successful:

```bash
git status
```

You should see output showing the current branch and that your working directory is clean.

> [!NOTE]
> You'll be on the default branch. If you want to access a different branch use:
> 
> ```git fetch --all```
> 
> ```git switch some-other-branch```

## Step 5: Configure environment variables

The application reads configuration from a `.env` file. Copy the example configuration:

```bash
cp .env.example .env
```

Edit the `.env` file with `nano`:

```bash
nano .env
```

Update the variables based on your deployment environment. For a local test installation, most defaults are suitable. If you need to customize database credentials, API keys, or ports, make those changes now. Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

## Step 6: Build and start the application

Start all services using Docker Compose:

```bash
docker compose up -d
```

The `-d` flag runs services in the background (detached mode).

This command will:
1. Build Docker images for custom services (Flask app and database initialization scripts)
2. Pull pre-built images (PostgreSQL, Grafana)
3. Create and start all containers
4. Initialize the database and load the CSV data
5. Configure the Grafana analytics dashboard

The initial startup takes 1–2 minutes. Monitor the startup process by checking container logs:

```bash
docker compose logs -f
```

Press `Ctrl+C` to exit the logs once all services have started.

## Step 7: Verify the installation and access the application

Once all containers are running, access the application in your browser:

- **Web application:** `http://vm-ip-goes-here:5000` — The main DineSafeViz application
- **Analytics dashboard:** `http://vm-ip-goes-here:3000` — Grafana dashboard for inspections and compliance data
