# Journal 95

## 2026-07-04 — README MVP revision per spec

**Task:** Implement `docs/ref/readme-mvp-spec.md` on branch `feat/main-readme-rf`.

### File inventory (pre-edit)

Verified all paths referenced in the spec resolve from repo root:
- `infra/ansible/vault/secrets.yml` ✓
- `infra/ansible/vault/example-secrets.yml` ✓
- `docker-compose.yml` ✓
- `docs/how-to/1-install/README.md` ✓
- `docs/how-to/3-redeploy-guide.md` ✓
- `docs/superpowers/specs/2026-06-09-aks-deployment-design.md` ✓
- `docs/superpowers/plans/2026-06-09-aks-deployment.md` ✓
- `docs/img/azure.drawio` ✓ (no PNG export → added TODO)
- `docs/ref/arch/README.MD` ✓ (uppercase — left as-is)
- All P2.3 arch docs (`arch-design-decision.md`, `arch-net.md`, `arch-ci-cd.md`, `arch-dr.md`, `arch-testing.md`) ✓
- No LICENSE file → skipped P2.4

### Changes applied to README.md

**P0.1** Fixed broken link `DineSafeViz/infra/ansible/vault/secrets.yml` → `infra/ansible/vault/secrets.yml`.

**P0.2** Rewrote information security paragraph: secrets are Ansible Vault AES256-encrypted; added link to example-secrets.yml template.

**P0.3** Removed placeholder "Evolution" section (`v x.y.z` entries). Section omitted per spec recommendation.

**P0.4** Spelling/grammar:
- "selfhosted" → "self-hosted" (two occurrences)
- "Small foot print" → "Small footprint"
- "visualises" → "visualizes"
- "configuration are retrieved" → "configuration is retrieved"
- Deleted stray bare path `docs/ref/arch/arch-monitoring.md` under Monitoring

**P1.1** Strengthened opening: added why-it-exists sentence, tech stack one-liner with links, on-prem status callout, `<!-- TODO: live demo URL -->`, and DineSafe dataset link.

**P1.2** Added Project status table near top; removed inline "Coming Soon (™️)" callouts.

**P1.3** Added "What's next: AKS migration" section linking the design spec and deployment plan; added `<!-- TODO: export azure.drawio to png -->`.

**P1.4** Added Getting Started lead-in distinguishing install vs. redeploy guide; noted DB seeding required.

**P2.3** Added "Further reading" links to five deeper arch docs (design decisions, networking, CI/CD, disaster recovery, testing).

**P2.4** Skipped — no LICENSE file.
