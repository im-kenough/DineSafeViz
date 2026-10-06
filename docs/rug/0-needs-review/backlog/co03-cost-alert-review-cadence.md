# CO:03 — Cost alert review cadence

- **From:** Cost Optimization C5 (Monitor and optimize over time)
- **Checklist item:** [CO:03](https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/collect-review-cost-data) — Collect and review cost data.
- **Phase:** 1
- **Status:** Not formalized

## What
- Set a recurring cadence to review cost alerts and actual spend vs. the $100
  cap (e.g. monthly).
- Adjust alert thresholds if usage patterns drift.

## Why
- Alerts only help if someone looks; a cadence turns them into a habit and
  catches threshold drift.

## Guidance ([CO:03](https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/collect-review-cost-data))
- Set **budget alerts** at 90% (ideal), 100% (target), 110% (over); add a
  **forecast alert** at 110%; enable **anomaly detection**.
- Review actual + amortized spend against budget on a set cadence (solo → a
  monthly self-review).
- Group costs by tags (`workload`, `environment`, `owner`) for a breakdown.
- Assign a responsible owner (DRI) — here, you.
- Azure: Cost Management budgets + anomaly detection; optional scheduled export
  for history beyond the 13-month retention.

## Done when
- A review interval is recorded in spec.md and the first review is done.
