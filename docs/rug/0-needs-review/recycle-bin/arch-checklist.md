# Architecture - Reading checklist

This is the ordered reading list of Azure Well-Architected Framework
(WAF) and Azure Architecture Center documents that inform the
DineSafeViz AKS architecture. Walk these in order; each entry notes what
the document gives you and how it maps to the DineSafeViz design.

Use this list alongside [arch-design-decision.md](arch-design-decision.md).
As each item is read, update the corresponding section of the Design
Decision doc with scope-in / scope-out / modified items, then tick the
checkbox here.

## Phase 0 - Justify the platform choice

- [ ] **Compute decision tree** —
  https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree
  - Justify AKS over Azure App Service, Container Apps, or Functions.
  - Output: one paragraph in the Design Decision doc explaining why AKS
    was chosen despite cheaper compute options existing. The honest
    answer is "portfolio signal for AKS practice" — name it.

- [ ] **Kubernetes options on Azure** —
  https://learn.microsoft.com/en-us/azure/aks/learn/concepts-clusters-workloads
  - Justify standard AKS over AKS Automatic or AKS Fleet Manager.

## Phase 1 - Anchor reference architecture (Phase 1 scope)

- [ ] **AKS Baseline Architecture** —
  https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks/baseline-aks
  - This is the "we implement a modified X" anchor.
  - Output: a conformance table in the Design Decision doc listing every
    baseline component, what DineSafeViz does, and the rationale for any
    divergence.

- [ ] **AKS Well-Architected service guide** —
  https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service
  - Umbrella WAF page for AKS. Acts as the table of contents for the
    per-pillar guides below.

## Phase 2 - Walk the Well-Architected Framework pillars for AKS

For each pillar, capture scope-in, scope-out, and modified items in the
Design Decision doc. Be explicit about scope-out items — silent
omissions read as oversight.

- [ ] **Reliability (AKS)** —
  https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service-reliability
- [ ] **Security (AKS)** —
  https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service-security
- [ ] **Cost Optimization (AKS)** —
  https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service-cost-optimization
- [ ] **Operational Excellence (AKS)** —
  https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service-operational-excellence
- [ ] **Performance Efficiency (AKS)** —
  https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-kubernetes-service-performance-efficiency

## Phase 3 - Day-2 operations

- [ ] **AKS Day-2 operations guide** —
  https://learn.microsoft.com/en-us/azure/architecture/operator-guides/aks/day-2-operations-guide
  - Cross-check the runbook table (RB-01..RB-16 in the design spec) for
    completeness.
  - Likely gap to add: an AKS version upgrade runbook.

## Phase 4 - Disaster recovery (Phase 1 scope)

- [ ] **Passive-cold solution for AKS** —
  https://learn.microsoft.com/en-us/azure/aks/passive-cold-solution
  - Cite as the reference pattern implemented in Phase 1 (GRS-replicated
    CNPG WAL archive, no running secondary cluster).

- [ ] **AKS multi-region best practices** —
  https://learn.microsoft.com/en-us/azure/aks/operator-best-practices-multi-region
  - Cross-check RPO ≤ 24h / RTO ≤ 4h targets.

## Phase 5 - Forward-looking (Phase 2 roadmap)

- [ ] **AKS Baseline for multi-region clusters** —
  https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-multi-region/aks-multi-cluster
  - Informs Phase 2; document the planned divergences from this
    reference now so the Phase 2 migration is a configuration change,
    not a redesign.

- [ ] **AKS Landing Zone Accelerator** —
  https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/scenarios/app-platform/aks/landing-zone-accelerator
  - Skim only. Cite as explicitly out of scope (single subscription,
    single tenant, no central policy).

## Optional - mention in passing

- Community AKS checklist — https://www.the-aks-checklist.com/
  - Useful cross-reference; note it as community-authored, not
    Microsoft-authoritative.
- Azure Well-Architected Mission-Critical workload guidance —
  https://learn.microsoft.com/en-us/azure/well-architected/mission-critical/mission-critical-overview
  - Explicitly out of scope. DineSafeViz is a portfolio demo, not
    mission-critical.
