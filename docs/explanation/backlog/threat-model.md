# Threat model

- **From:** Security S5 (Sustain and evolve posture); supports S2
- **Phase:** 2
- **Status:** Not started

## What
- Lightweight threat model of the workload (STRIDE or attack-tree).
- Focus on the exposed surface: public ingress, AKS API server, Key Vault, ACR,
  the Postgres credentials path.

## Why
- Surfaces attack vectors before implementation and prioritizes which controls
  matter most for the budget.

## Done when
- A prioritized list of threats + chosen mitigations/compensating controls.
