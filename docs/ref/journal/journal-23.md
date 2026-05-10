# Journal 23 — Homelab K8s Infrastructure Design

## 2026-05-01 14:00
**Session start: Planning homelab Kubernetes deployment**

- User wants to deploy DineSafeViz on a Proxmox homelab
- Target: 2 master nodes, 3 worker nodes on Ubuntu VMs
- Specs: 4 CPU all nodes, 4GB RAM masters, 8GB RAM workers
- Tools: Terraform (VM provisioning) + Ansible (K8s config)
- App: 1-3 replicas (min 1, max 3)
- Purpose: dev testing environment

Explored project context:
- Current stack: Docker Compose with Flask (port 5000), PostgreSQL 17.9, Grafana 11.6.0, init-grafana sidecar
- 4 services total, all on a single Docker Compose network
- No existing infrastructure-as-code or K8s manifests
- Tech: Python 3.14-slim Flask app, Jinja2 templates, vanilla JS frontend
- Data: ~6.5MB CSV loaded into PostgreSQL on init
- Existing docs at docs/ref/infra/ (mostly stubs)

Starting brainstorming process for infrastructure design.

## 2026-05-01 14:10
**Decision: VM provisioning method**

User chose: Cloud image with cloud-init template approach.
- Create an Ubuntu cloud image template on Proxmox (once, manually or scripted)
- Terraform clones from that template for each K8s node
- cloud-init handles SSH keys, hostname, network config per-node
- Include template creation instructions in the design spec

## 2026-05-01 14:15
**Decision: K8s distribution**

User chose: kubeadm (option A) — full upstream Kubernetes.
- Need to plan: etcd (stacked on masters), CNI plugin, control plane HA
- Ansible will handle kubeadm init on first master, join on remaining nodes
- More setup steps than k3s but standard K8s experience

## 2026-05-01 14:18
**Decision: CNI plugin**

User chose: Flannel (option B) — simple VXLAN overlay.
- Lightweight, minimal config, good fit for homelab dev
- No network policies (not needed for dev testing)

## 2026-05-01 14:20
**Decision: Service exposure**

User chose: NodePort (option A) — simplest approach.
- No MetalLB or Ingress controller needed
- Access via <node-ip>:30XXX
- Keeps the stack minimal for dev testing

## 2026-05-01 14:25
**Decision: Storage and PostgreSQL**

User chose: Longhorn (option A) for distributed block storage.
- Dynamic PVC provisioning via StorageClass, closest to Azure AKS experience
- PostgreSQL runs as StatefulSet with Longhorn-backed PVC
- Data replicates across worker nodes
- Same PVC manifests will work on Azure (just swap StorageClass)
- Motivated by wanting cloud-parity for eventual Azure deployment

## 2026-05-01 14:30
**Decision: Container registry**

User chose: ghcr.io (GitHub Container Registry)
- Free, private images on GitHub free tier (500MB)
- Existing GitHub Actions can build and push images
- K8s nodes pull via imagePullSecret with a GitHub PAT
- Plan to migrate to Azure ACR later (no free tier, ~$5/mo Basic)

## 2026-05-01 14:45
**Implementation plan written**

Wrote full implementation plan to docs/superpowers/plans/2026-05-01-homelab-k8s.md
- 16 tasks covering: scaffold, Terraform, DB Dockerfile, Ansible (config, 4 roles, playbooks, vault), K8s manifests (namespace, db, web, grafana, init-grafana), GitHub Actions, final validation
- Key deviation from spec: Dinesafe.csv is 6.5MB, exceeds 1MB ConfigMap limit. Used custom postgres Docker image (src/dsv-db/Dockerfile) instead of ConfigMap.
- Self-review fixes: PostgreSQL readiness probe needed shell wrapper for env var expansion; Grafana deployment was missing dinesafe.json dashboard volume mount.

## 2026-05-01 14:35
**Decision: Secrets management**

User chose: Ansible Vault for dev/homelab.
- Encrypts secrets in Ansible, injected into K8s Secrets during deployment
- No extra tooling — already using Ansible
- Future: Azure Key Vault (~$0.03/10k ops, effectively free at low scale)

## 2026-05-01 14:38
**Decision: Network configuration**

- Proxmox host: 10.0.20.21/24
- DHCP range: 10.0.20.200-254
- Bridge: vmbr0
- Will use static IPs outside DHCP range for K8s VMs (e.g., 10.0.20.50-54)
- cloud-init will configure static IPs per node

## 2026-05-01 14:42
**Decisions: Structure and final IPs**

Repo structure: Approach A — monorepo with `infra/` directory.
- Future intent: migrate to Approach C (Helm charts) for multi-environment support

Gateway: 10.0.20.1/24

Final IP assignments (updated — 3 masters for etcd quorum):
| Node         | Role          | IP           |
|--------------|---------------|--------------|
| k8s-master1  | control plane | 10.0.20.70   |
| k8s-master2  | control plane | 10.0.20.71   |
| k8s-master3  | control plane | 10.0.20.72   |
| k8s-worker1  | worker        | 10.0.20.73   |
| k8s-worker2  | worker        | 10.0.20.74   |
| k8s-worker3  | worker        | 10.0.20.75   |

Changed from 2 masters to 3 for proper etcd quorum (odd number).
6 VMs total: 3x 4CPU/4GB (masters) + 3x 4CPU/8GB (workers) = 24 CPU, 36GB RAM.
Post-setup optimization: drop to 3x 4CPU/2GB (masters) + 3x 4CPU/4GB (workers) = 24 CPU, 18GB RAM.
