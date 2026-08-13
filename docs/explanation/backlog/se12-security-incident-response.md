# SE:12 — Security incident response plan

- **From:** Security S1 (Plan your security readiness)
- **Checklist item:** [SE:12](https://learn.microsoft.com/en-us/azure/well-architected/security/incident-response) — Define and test incident response procedures.
- **Phase:** 2
- **Status:** Not written

## What
- Brief IR plan: preparedness, detection, containment, mitigation, post-incident.
- Map to who does what (solo owner) and which signals trigger it.

## Why
- Avoids improvised decisions during a real security event; the readiness half
  of the Security pillar.

## Guidance ([SE:12](https://learn.microsoft.com/en-us/azure/well-architected/security/incident-response))
- Designate an **incident notification contact**; ensure alerts arrive with
  enough context and next steps, and keep an audit trail.
- **Triage**: determine the attack vector and impact on confidentiality /
  integrity / availability; assign a severity; decide contain vs. shut down
  (shutdown → DR process).
- **Recover** treating it like a disaster — ensure the fix prevents recurrence
  (don't restore the vulnerability); validate failover/failback.
- **Learn**: RCA + blameless postmortem; update the IR plan and security
  baseline. Keep a single adjustable playbook, not many.
- Define a communication plan and a standard incident-report format.
- Note any legal/regulatory reporting windows (here: minimal — public data).

## Done when
- One-page IR plan exists and references the detection signals in place.
