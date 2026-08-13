# SE:02 — Threat model

- **From:** Security S5 (Sustain and evolve posture); supports S2
- **Checklist item:** [SE:02](https://learn.microsoft.com/en-us/azure/well-architected/security/secure-development-lifecycle) — Threat modeling within the secure development lifecycle.
- **Phase:** 2
- **Status:** Not started

## What
- Lightweight threat model of the workload (STRIDE or attack-tree).
- Focus on the exposed surface: public ingress, AKS API server, Key Vault, ACR,
  the Postgres credentials path.

## Why
- Surfaces attack vectors before implementation and prioritizes which controls
  matter most for the budget.

## Guidance ([SE:02](https://learn.microsoft.com/en-us/azure/well-architected/security/secure-development-lifecycle))
- Define **scope**: system boundaries + asset inventory; focus on the exposed
  surface listed above.
- Capture each component's **data flows and dependencies**.
- Analyze each from an attacker's perspective; adopt **assume-breach** +
  defense-in-depth.
- Use **STRIDE** to classify threats (spoofing, tampering, repudiation, info
  disclosure, DoS, elevation of privilege).
- Document each threat, its mitigating control, and the response if the control
  fails; assign an owner + timeline.
- Track results and revisit as the architecture evolves.
- Tool: Microsoft Threat Modeling Tool.

## Done when
- A prioritized list of threats + chosen mitigations/compensating controls.
