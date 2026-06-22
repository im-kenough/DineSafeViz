# 2026-06-22 17:01

- Consolidating GitHub Actions in `docs/ref/arch/design-planning/arch-design-aks.md`.
- Replaced the wrapper jobs for `_start-aks-cluster`, `_stop-aks-cluster`, `_deploy-application`, `_failback-to-primary-environment`, and `_deploy-monitoring` with single, parameterized GitHub Actions workflows that accept the environment via a dropdown. This simplifies maintenance and matches modern GHA practices (`workflow_dispatch` with choices).
