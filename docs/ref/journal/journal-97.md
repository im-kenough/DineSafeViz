# Journal 97

## 2026-06-16 — Complete technology choice sections in arch-design-planning.md

### Context

Continuing architecture planning for DineSafeViz deployment on AKS. The
`docs/ref/arch/arch-design-planning.md` file has empty or stub sections for
several Azure technology choice categories. Dispatching parallel subagents to
research and write each section using the Microsoft Azure Architecture Centre
articles.

### Sections to complete

- Choose an identity service (new section, not yet in doc)
- Choose a data store (empty heading at line 204)
- Choose an analytics solution (empty heading at line 206)
- Choose a networking service (empty heading at line 212)
- Choose an integration and automation service (new section, not yet in doc)

### Approach

Each subagent fetches the relevant Microsoft docs, evaluates candidates against
DineSafeViz's requirements (AKS, single-region, no on-prem AD, small footprint,
cost-conscious), and writes its section content to a temp file. Main agent then
integrates all temp file output into the planning document.

### Work log

#### 2026-06-16 — Dispatched parallel research agents

Launched 5 background agents simultaneously, one per section. Each agent was
given the app context (AKS, PostgreSQL, Grafana, single-region, cost-conscious,
no on-prem AD) and all reference article URLs for its section.

Agents returned content as inline text (most could not write to /tmp due to
permissions); content was saved manually to temp files and then integrated into
the main document using the Edit tool.

#### 2026-06-16 — Integrated all sections into arch-design-planning.md

Edits made to `docs/ref/arch/arch-design-planning.md`:

- Inserted `### Choose an identity service` between the hybrid service section
  and the data store section (line ~204). Decision: Microsoft Entra ID with AKS
  Workload Identity (OIDC federation); hybrid auth article noted as out of scope.
- Filled `### Choose a data store` (was empty heading). Decision: Azure Database
  for PostgreSQL — Flexible Server (free tier); all 8 reference articles linked
  inline; ADF, data lake, and search options noted as not applicable.
- Filled `### Choose an analytics solution` (was empty heading). Decision:
  Grafana self-hosted in AKS; all 5 reference articles linked; batch and stream
  processing noted as not applicable.
- Filled `### Choose a networking service` (was empty heading). Decision: nginx
  ingress controller in-cluster; all Azure load-balancing services rejected on
  cost or scope grounds; VNet peering noted as not applicable.
- Appended `### Choose an integration and automation service` after the messaging
  section. Decision: all four services (Power Automate, Logic Apps, Functions,
  WebJobs) not applicable; GitHub Actions handles all automation.

Final section order verified:
  Compute → Container → Hybrid → Identity → Data Store → Analytics →
  AI (N/A) → Networking → Messaging (N/A) → Integration (N/A)
