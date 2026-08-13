# Incident-review process

- **From:** Reliability R4 (Design for operations)
- **Checklist item:** [OE:08](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/incident-response) — Establish a structured incident management process.
- **Phase:** 3
- **Status:** To be established

## What
- Define a lightweight blameless post-incident review: template, when it
  triggers, where write-ups live.

## Why
- Turns real production incidents into design/ops improvements — the R4
  "learn from incidents" loop.

## Guidance ([OE:08](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/incident-response))
- Document a core incident-response plan: **roles** (incident manager, technical
  lead, comms), **communication/escalation**, and detect → triage → contain →
  recover procedures.
- After each incident: run an **RCA** + **blameless postmortem** with an
  impartial facilitator.
- Capture actionable items in three buckets: refine the IR plan, improve
  observability, improve workload design.
- Keep audit trails (config changes, deployments) to reconstruct incidents.
- Test the plan periodically with dry runs.

## Done when
- A one-page template exists and is used after the first incident.
