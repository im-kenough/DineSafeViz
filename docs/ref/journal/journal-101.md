# Journal 101

## 2026-06-19 — AKS Automatic vs AKS Standard cost comparison

### Context

User asked whether the current AKS design assumes AKS Standard mode and how
much more expensive AKS Automatic would be.

### Work log

Grepped arch docs to confirm current AKS design assumptions:
- Design uses **AKS Standard mode** (manually configured node pools: `syspool`
  1–2, `usrpool` 1–3, cluster autoscaler enabled).
- Pricing tier: **AKS Free** control plane tier (not Standard tier). The brief
  notes this "Saves ~$73/mo per cluster vs Standard."

Key distinction explained to user: "AKS Standard" refers to two different
things — the **cluster mode** (Standard vs Automatic) and the **pricing tier**
(Free / Standard / Premium). Current design uses Standard mode + Free tier.

AKS Automatic requires Standard or Premium pricing tier; would add at minimum
$73/mo per cluster to the current design's cost.

---
