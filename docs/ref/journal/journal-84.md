# Journal 84 — Azure component inventory, region independence, subscription model diagrams

## 2026-06-10 — Session start

**Goal:** Answer user questions about:
1. Microsoft's Well-Architected equivalent (Azure WAF, answered in previous session)
2. Overhead of 1 vs 2 Azure subscriptions (answered in previous session)
3. Draw current-design diagram vs 3-subscription model diagram
4. Clarify which Azure services are region-independent
5. Write a component inventory for a single prod deployment to a .md file

**Context:** Current design spec at `docs/superpowers/specs/2026-06-09-aks-deployment-design.md`.
No Azure Terraform has been written yet — Epic 2 is next.

## 2026-06-10 — Writing component inventory doc

Writing to `docs/ref/azure-component-inventory.md`. Covers:
- Region independence table (DNS global, ACR regional-data/global-endpoint, rest regional)
- ASCII diagram: current design (single subscription, 3 RGs)
- ASCII diagram: 3-subscription model (shared + prod + non-prod subs)
- Full component list: single prod deployment, split by who provisions what
  (Terraform-managed, AKS node RG auto-provisioned, K8s-provisioned)
