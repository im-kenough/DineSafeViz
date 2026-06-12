# Journal 83 — Designing Azure AKS deployment (Phase 1)

## 2026-06-09 — Session start: AKS design brainstorm

**Goal:** Work through design questions and produce a spec for deploying
DineSafeViz on Azure AKS. Phase 1 target: 1 AKS cluster, 1 app instance in
1 availability zone. User has not provisioned anything in Azure yet.

**User's opening questions:**
1. Use `dinesafeviz.ca` as staging URL (prod = `dinesafeviz.com`)?
2. Best-practice enterprise-mimicking process on a personal budget?
3. How to handle the database?
4. How do Azure spot instances work as AKS nodes — does AKS provision a
   replacement before eviction?

**Prior art found:**
- `docs/superpowers/specs/2026-05-01-homelab-k8s-design.md` — kubeadm on
  Proxmox VMs, with explicit Azure migration paths noted (Longhorn→Azure
  Disk, ghcr.io→ACR, Vault→Key Vault, raw YAML→Helm).
- `infra/` already has terraform/ansible/packer for the Proxmox path.
- App is Flask + Postgres + Grafana, 3 main services + 2 init containers.
- Recent data fix: DB tables include 464K historical rows + ~107K recent
  rows (reseedable from Toronto Open Data CSVs).

**Approach for this session:** Follow superpowers:brainstorming. Will work
through clarifying questions one at a time before proposing approaches
and writing the spec to `docs/superpowers/specs/2026-06-09-aks-...md`.

## 2026-06-09 — Decisions locked in via Q&A

- Azure role: prod + staging in Azure; homelab kept as sandbox.
- Budget: USD $25-50/mo lean tier.
- Domain: buy `dinesafeviz.com`, staging at `stg.dinesafeviz.com`. Skip `.ca`.
- DB layer: CloudNativePG in-cluster, WAL archive to Azure Blob GRS.
- RPO/RTO: ≤24h / ≤4h (matches "daily sync is sufficient").
- Cluster lifecycle: stopped by default, GHA `aks-up`/`aks-down`/`aks-scale`.
- Node pool mix: 1 on-demand system pool + 1 spot user pool.
- Region pair: East US 2 (primary) + West US 2 (Phase 2 DR).
- DNS: Azure DNS.
- Registry: ACR Basic.
- Ingress: NGINX Ingress Controller + cert-manager (LE DNS-01).
- Phase 2: tiny Azure Static Web App landing page with a "wake the demo" button.

## 2026-06-09 — User feedback on Section 1 (architecture overview)

User asked to explain system vs user node pools, and stated desired autoscaling:
- min 1 system + 1 user node, max 2 system + 3 user nodes
- pools spread across AZs
- same config for prod, dev (interpretation pending — shared cluster?), DR
- demonstrate autoscaling capability in IaC even with no real traffic

User asked if cheaper PVC storage is possible — yes, Standard SSD (E10) saves
~USD $5/mo over Premium SSD with no real impact at our IOPS profile.

## 2026-06-09 — Mid-design adjustments

- After Section 1: cluster topology changed to **separate prod + staging
  clusters** (was single cluster, two namespaces). Cost delta ~USD $12/mo,
  better security/ops story matches user's stated goal.
- After Section 3: repo will be flipped from private to public so
  GitHub Environments-based federated identity subjects work on Free tier.
  Required-reviewer approval gates available on `prod` env.
- After Section 5: user requested `grafana` → `analytics` rename throughout
  the chart, templates, values, KV secret names, NetworkPolicy names, etc.
  Rationale: future separate Grafana instance for platform monitoring should
  own the `grafana` / `monitoring` namespace; the data-viz Grafana is the
  *analytics* component. Existing docker-compose already used `dsv-analytics`,
  so this aligns with prior convention. Retroactively applied to Sections 3
  and 5; will be applied across the spec when written.

## 2026-06-09 — All 8 sections approved; writing spec doc

User said "continue" through Sections 5, 6 (workflows), 7 (failure modes +
runbooks + observability), 8 (cost summary + Phase 2/3 roadmap). All
approved. Phase 1 cost target ~USD $35.75/mo at stated usage, inside the
$25-50 lean tier.

Writing consolidated spec to
`docs/superpowers/specs/2026-06-09-aks-deployment-design.md`.

## 2026-06-09 — Spec written + self-review complete

Spec written to `docs/superpowers/specs/2026-06-09-aks-deployment-design.md`.
Self-review pass found one minor gap (NS delegation procedure detail at
Namecheap) and fixed inline. No placeholders, no internal contradictions,
no scope creep. Ready for user review.

Per user's CLAUDE.md "only commit when explicitly asked," not auto-committing.
Will ask user to review and confirm commit.

## 2026-06-10 — User approved spec; created implementation plan + GH issues

User said "the spec looks good." Asked to write implementation plan AND
create high-level GitHub issues with relevant sub-tasks, proper
dependency ordering, tagged appropriately, in milestone v0.4.0.

Wrote implementation plan to
`docs/superpowers/plans/2026-06-09-aks-deployment.md` covering 13 Epics:
1. Public repo + GH Environments setup
2. Shared Azure infra (Terraform)
3. Image build + terraform-shared workflows
4. Staging Azure infra (AKS, KV, WAL storage)
5. Cluster bootstrap Helm chart
6. DineSafeViz app Helm chart
7. AKS lifecycle workflows (aks-up/down/scale, app-deploy)
8. Staging E2E validation
9. Prod Azure infra
10. Prod deployment + DNS cutover
11. Observability hookup
12. Scheduled operational workflows
13. Documentation refresh

Created 14 GH issues:
- Parent tracking issue: #141
- Epic 1: #142 (no blocked-by)
- Epic 2: #143 (← #142)
- Epic 3: #144 (← #143)
- Epic 4: #145 (← #143)
- Epic 5: #146 (← #145)
- Epic 6: #147 (← #144, #146)
- Epic 7: #148 (← #145)
- Epic 8: #149 (← #147, #148)
- Epic 9: #150 (← #149)
- Epic 10: #151 (← #150)
- Epic 11: #152 (← #151)
- Epic 12: #153 (← #151)
- Epic 13: #154 (← #152, #153)

All issues assigned to im-kenough, milestone v0.4.0, labeled per
existing repo label taxonomy (iac, infra, infosec, ci-cd, db, ops, dr,
documentation, chore, github_actions). Parent #141 includes ASCII
dependency graph + child checklist.

## 2026-06-10 — Expanded #142 + created #155 for pre-IaC manual prereqs

User asked: "what do I need to do manually before I direct you to write
the new AKS IAC? What do I need to do to the repo? what do I need to
provision for Azure? give me requirements as github issues. modify/
create them if they don't exist"

Audited #142 against the full pre-IaC manual surface. Gaps found:
local toolchain install, Azure Owner-role verification, resource provider
registration, MFA enable, subscription-wide budget alert, the missing
`dsv-shared` environment. Domain registration also missing as its own
issue (different timing — independent of IaC writing; only blocks #151
prod DNS cutover).

Actions taken:

- **Modified #142** — retitled to `chore(ci-cd,infra): epic 1 — pre-IaC
  manual prerequisites`. Body restructured into five sub-sections:
  Repo hygiene / GitHub Environments (now including `dsv-shared`) /
  Local toolchain (az, terraform, kubectl, helm, helmfile + kubelogin) /
  Azure account (MFA, Owner verification, RP registration, $50/mo
  budget) / GitHub repo variables / Branch + commit. Acceptance criteria
  rewritten as explicit verifiable bullets. Out-of-scope section calls
  out #155 (domain) and Epic 2 Step 1 (TF state bootstrap) so future
  agents don't duplicate or conflate.

- **Created #155** — `chore(infra): domain registration — buy
  dinesafeviz.com from Namecheap`. Labels: chore, infra, infosec.
  Milestone: v0.4.0. Blocked-by: none. Blocks: #151 (prod deploy +
  DNS cutover). Body covers purchase, registrar hygiene (2FA,
  registrar lock, auto-renew, EPP storage), and pre-cutover notes
  for #151 (without executing the NS swap).

- **Updated #141** — added #155 to checklist (parallel-to-#142
  positioning); redrew the ASCII dependency graph showing #155 as
  a side-channel that converges into #151; updated acceptance
  criteria to "All 13 child epics + #155 closed".

Decision rationale for the split: keeping domain purchase in a separate
issue avoids tangling personal-billing/registrar work with developer-
workstation setup, and reflects real-world dependency — IaC writing
can proceed in full without the domain existing; only the cutover
step needs it.

Cost flag: USD ~$13/yr for `.com`. No free alternative noted that
suits portfolio use. Budget alert of $50/mo added to #142 to cover
both monthly Azure spend + amortized domain.
