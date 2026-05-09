# Homelab Kubernetes Deployment — Design Spec

**Date:** 2026-05-01
**Purpose:** Deploy DineSafeViz on a Proxmox homelab Kubernetes cluster for dev testing.

## Summary

Provision 6 Ubuntu VMs on a single Proxmox host using Terraform, bootstrap a kubeadm Kubernetes cluster with Ansible, and deploy DineSafeViz services via K8s manifests. All infrastructure-as-code lives in `infra/` within the existing monorepo.

## Infrastructure Overview

### Proxmox Host

- **Host IP:** 10.0.20.21/24
- **Gateway:** 10.0.20.1
- **Bridge:** vmbr0
- **DHCP range:** 10.0.20.200-254 (VMs use static IPs outside this range)
- **DNS:** 10.0.20.1 (gateway, assumed to be router providing DNS)

### VM Specifications

| Node | Role | IP | CPU | RAM (setup) | RAM (post-setup) |
|------|------|----|-----|-------------|-------------------|
| k8s-master1 | control plane | 10.0.20.70 | 4 | 4GB | 2GB |
| k8s-master2 | control plane | 10.0.20.71 | 4 | 4GB | 2GB |
| k8s-master3 | control plane | 10.0.20.72 | 4 | 4GB | 2GB |
| k8s-worker1 | worker | 10.0.20.73 | 4 | 8GB | 4GB |
| k8s-worker2 | worker | 10.0.20.74 | 4 | 8GB | 4GB |
| k8s-worker3 | worker | 10.0.20.75 | 4 | 8GB | 4GB |

**Setup totals:** 24 vCPU, 36GB RAM
**Post-setup totals:** 24 vCPU, 18GB RAM

3 masters provide proper etcd quorum (tolerates 1 master failure).

### OS

- Ubuntu 24.04 LTS (cloud image with cloud-init)

## Technology Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| VM provisioning | Terraform (bpg/proxmox provider) | IaC for reproducible VM creation |
| VM template | Ubuntu 24.04 cloud image + cloud-init | Automatable, no manual OS install |
| Cluster config | Ansible | Configures K8s, deploys app, manages secrets |
| K8s distribution | kubeadm | Full upstream Kubernetes, standard experience |
| CNI plugin | Flannel | Simple VXLAN overlay, low overhead |
| Storage | Longhorn | Dynamic PVC provisioning, closest to Azure Disk experience |
| Service exposure | NodePort | Simplest option, sufficient for dev testing |
| Container registry | ghcr.io | Free, private, integrates with existing GitHub Actions |
| Secrets management | Ansible Vault | No extra tooling, encrypts secrets at rest |
| Repo structure | Monorepo (`infra/` directory) | Simple, app and infra evolve together |

### Future migration path

- **Storage:** Longhorn StorageClass swaps to Azure Disk StorageClass (PVC manifests unchanged)
- **Registry:** ghcr.io migrates to Azure ACR (~$5/mo Basic tier)
- **Secrets:** Ansible Vault migrates to Azure Key Vault (~$0.03/10k ops)
- **Manifests:** Plain K8s YAML migrates to Helm charts (Approach C) for multi-environment templating

## VM Template Creation (One-Time Proxmox Setup)

Steps to run on the Proxmox host (`10.0.20.21`):

1. Download the Ubuntu 24.04 cloud image:
   ```bash
   wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img \
     -O /var/lib/vz/template/iso/ubuntu-24.04-cloud.img
   ```

2. Create a VM shell (ID 9000 by convention):
   ```bash
   qm create 9000 --name ubuntu-2404-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
   ```

3. Import the cloud image as a disk:
   ```bash
   qm importdisk 9000 /var/lib/vz/template/iso/ubuntu-24.04-cloud.img local-lvm
   ```

4. Attach the disk and configure boot:
   ```bash
   qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
   qm set 9000 --boot c --bootdisk scsi0
   ```

5. Add cloud-init drive and serial console:
   ```bash
   qm set 9000 --ide2 local-lvm:cloudinit
   qm set 9000 --serial0 socket --vga serial0
   ```

6. Enable QEMU guest agent:
   ```bash
   qm set 9000 --agent enabled=1
   ```

7. Convert to template:
   ```bash
   qm template 9000
   ```

## Terraform — VM Provisioning

### Structure

```
infra/terraform/
├── main.tf              # Proxmox provider, VM resource definitions
├── variables.tf         # Node specs, IPs, template ID, SSH key
├── outputs.tf           # Node IPs and hostnames for Ansible inventory
└── terraform.tfvars     # Actual values (gitignored)
```

### What Terraform Does

- Connects to Proxmox API on the host
- Clones VM template 9000 six times
- Configures each clone via cloud-init: hostname, static IP, gateway, DNS, SSH public key
- Sets CPU and RAM per role (4 CPU all; 4GB masters, 8GB workers during setup)
- Disk: 20GB per node (expandable later)
- Outputs node IPs and names for Ansible to consume

### Provider

Uses the `bpg/proxmox` Terraform provider to communicate with the Proxmox VE API.

## Ansible — Cluster Bootstrap & App Deployment

### Structure

```
infra/ansible/
├── inventory/
│   └── hosts.yml            # Static inventory: masters + workers groups
├── group_vars/
│   ├── all.yml              # K8s version, pod CIDR, flannel version
│   ├── masters.yml          # Master-specific config
│   └── workers.yml          # Worker-specific config
├── playbooks/
│   ├── site.yml             # Full setup (runs all below in order)
│   ├── common.yml           # OS prep on all nodes
│   ├── masters.yml          # kubeadm init + join control plane
│   ├── workers.yml          # kubeadm join workers
│   ├── cluster-addons.yml   # Flannel, Longhorn, secrets
│   └── deploy-app.yml       # Apply K8s manifests (rerunnable)
├── roles/
│   ├── common/              # Disable swap, install containerd, kubeadm/kubelet/kubectl
│   ├── master/              # kubeadm init, kubeconfig, join token
│   ├── worker/              # kubeadm join
│   └── addons/              # Flannel CNI, Longhorn, imagePullSecret
└── vault/
    └── secrets.yml          # Ansible Vault encrypted
```

### Playbook Flow

1. **common.yml** (all 6 nodes):
   - apt update/upgrade
   - Disable swap (required by kubelet)
   - Load kernel modules: `overlay`, `br_netfilter`
   - Set sysctl: `net.bridge.bridge-nf-call-iptables`, `net.ipv4.ip_forward`
   - Install containerd (container runtime)
   - Install kubeadm, kubelet, kubectl
   - Enable kubelet service

2. **masters.yml**:
   - `kubeadm init` on k8s-master1 with `--control-plane-endpoint=10.0.20.70:6443` and `--upload-certs`
   - Pod network CIDR: `10.244.0.0/16` (Flannel default)
   - Copy kubeconfig to ansible user
   - Generate join commands (control-plane + worker)
   - `kubeadm join` on k8s-master2 and k8s-master3 as control plane nodes

3. **workers.yml**:
   - `kubeadm join` on k8s-worker1, k8s-worker2, k8s-worker3 using token from master1

4. **cluster-addons.yml**:
   - Apply Flannel CNI manifest
   - Install Longhorn (`kubectl apply -f` from Longhorn's release manifest)
   - Create `dinesafeviz` namespace
   - Create K8s Secrets from Ansible Vault values (DB creds, Grafana creds, ghcr.io PAT)
   - Create `imagePullSecret` for ghcr.io

5. **deploy-app.yml** (rerunnable for updates):
   - Apply all K8s manifests from `infra/k8s/`
   - Can be run independently to redeploy the app

### Vault Contents

Encrypted with `ansible-vault`:
- `db_user`, `db_password`, `db_name` — PostgreSQL credentials
- `gf_admin_user`, `gf_admin_password` — Grafana admin credentials
- `ghcr_pat` — GitHub PAT for image pulls

## K8s Manifests — Application Deployment

### Structure

```
infra/k8s/
├── namespace.yaml
├── secrets.yaml.example        # Template showing required keys
├── web/
│   ├── deployment.yaml         # Flask app, 1-3 replicas (HPA)
│   └── service.yaml            # NodePort service
├── db/
│   ├── statefulset.yaml        # PostgreSQL with Longhorn PVC
│   ├── service.yaml            # ClusterIP (internal only)
│   ├── configmap.yaml          # init.sql + Dinesafe.csv reference
│   └── pvc.yaml                # Longhorn-backed PVC
├── grafana/
│   ├── deployment.yaml         # Grafana with provisioning configs
│   ├── service.yaml            # NodePort service
│   ├── configmap.yaml          # Datasource + dashboard provisioning
│   └── pvc.yaml                # Longhorn-backed PVC
└── init-grafana/
    └── job.yaml                # One-shot K8s Job
```

### Docker Compose to K8s Mapping

| Docker Compose | K8s Equivalent |
|----------------|----------------|
| `services.web` | Deployment (1-3 replicas) + NodePort Service |
| `services.db` | StatefulSet (1 replica) + ClusterIP Service + Longhorn PVC |
| `services.grafana` | Deployment (1 replica) + NodePort Service + Longhorn PVC |
| `services.init-grafana` | Job (runs once, `restartPolicy: Never`) |
| `.env` variables | K8s Secrets + ConfigMaps |
| Named volumes (`dsv-db-data`, `dsv-analytics-data`) | Longhorn PersistentVolumeClaims |
| `depends_on` + healthchecks | Init containers + readiness probes |
| Docker Compose network | K8s Services (ClusterIP for internal, NodePort for external) |

### Web Deployment

- Image: `ghcr.io/<owner>/dinesafeviz:<tag>`
- Replicas: min 1, max 3 (HorizontalPodAutoscaler)
- `imagePullSecrets` referencing ghcr.io credentials
- Environment variables from K8s Secrets
- Readiness probe on Flask health endpoint
- NodePort exposes the app on all nodes

### PostgreSQL StatefulSet

- Image: `postgres:17.9`
- 1 replica (single-instance, data reproducible from CSV)
- Longhorn PVC for `/var/lib/postgresql/data`
- ConfigMap mounts `init.sql` and references `Dinesafe.csv`
- ClusterIP service (internal access only, no external exposure)
- Readiness probe: `pg_isready`

### Grafana Deployment

- Image: `grafana/grafana:11.6.0`
- 1 replica
- Longhorn PVC for `/var/lib/grafana`
- ConfigMap with datasource and dashboard provisioning YAML
- Environment variables from K8s Secrets
- NodePort exposes Grafana admin
- Readiness probe on `/api/health`

### Init-Grafana Job

- Image: `curlimages/curl:latest`
- K8s Job (`restartPolicy: Never`, `backoffLimit: 3`)
- Waits for Grafana readiness, then grants Viewer RBAC permissions
- Replaces Docker Compose's `restart: "no"` one-shot container

## CI/CD — GitHub Actions

### Image Build Pipeline

Extends existing `.github/workflows/release.yml`:

```
Push tag (v*) → GitHub Actions:
  1. Run tests (pytest)
  2. Build Docker image from src/dsv-app/Dockerfile
  3. Tag as ghcr.io/<owner>/dinesafeviz:<version> and :latest
  4. Push to ghcr.io
```

### Deployment

Manual — run from workstation:

```bash
# Full cluster setup (first time)
cd infra/terraform && terraform apply
cd infra/ansible && ansible-playbook playbooks/site.yml --ask-vault-pass

# App updates only (subsequent deploys)
cd infra/ansible && ansible-playbook playbooks/deploy-app.yml --ask-vault-pass
```

## Access

- **Flask web app:** `http://<any-node-ip>:<nodeport>` (NodePort in 30000-32767 range)
- **Grafana admin:** `http://<any-node-ip>:<grafana-nodeport>`
- **kubectl:** From workstation using kubeconfig copied from k8s-master1

## Files to .gitignore

```
infra/terraform/terraform.tfvars
infra/terraform/.terraform/
infra/terraform/*.tfstate*
infra/k8s/secrets.yaml
```

Note: `infra/ansible/vault/secrets.yml` is Ansible Vault encrypted and safe to commit.
