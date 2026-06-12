# Journal 86 — Draft architecture design decision doc and reading checklist

## 2026-06-10 — Session start

**Goal:** Adapt Azure Well-Architected practices for AKS to DineSafeViz.
Produce two artifacts:

1. `docs/ref/arch/arch-checklist.md` — ordered reading list of Azure
   Well-Architected and Architecture Center documents to work through.
2. `docs/ref/arch/arch-design-decision.md` — Design Decision doc draft
   that anchors the DineSafeViz AKS design to the AKS Baseline reference
   architecture and the passive-cold DR pattern, with per-pillar WAF
   scaffolds to fill in as reading progresses.

**Inputs:**

- Design spec: `docs/superpowers/specs/2026-06-09-aks-deployment-design.md`
- Prior research: `docs/ref/journal/journal-85.md` (AKS Architecture
  Center pattern comparison).

**Approach:** Draft from what the spec already states; mark per-pillar
checklist sections as TODO with concrete pointers to which Microsoft
guide to read. Avoid inventing Microsoft checklist contents not yet
verified.

## 2026-06-10 — Wrote arch-checklist.md

Created the reading list as a literal checklist (`- [ ]` markers) so
items can be ticked off as the user reads. Five phases plus optional
references.

## 2026-06-10 — Drafted arch-design-decision.md

Replaced the two-line stub with a structured draft:

- Context and scope statement.
- Reference architectures implemented (AKS Baseline modified,
  passive-cold DR, Phase 2 multi-region).
- AKS Baseline conformance table — populated from the spec (matches,
  divergences, rationale per row).
- Per-pillar WAF scaffolds (Reliability, Security, Cost, Operational
  Excellence, Performance Efficiency). Each pillar has confident
  scope-in/scope-out items derived from the spec and a TODO block for
  items requiring the actual WAF checklist.
- Out-of-scope reference architectures (Landing Zone, Mission-Critical).
- Decision log section as a placeholder for ad-hoc decisions captured
  later.
