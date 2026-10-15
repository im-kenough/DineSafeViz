# Inspection Analytics

This page describes how the inspections analytics dashboard works.

Grafana uses the postgresql db as datasource and queries using a custom dashboard. It shows statistics and metrics about the
DineSafe dataset, not used for infrastructure monitoring.

`/dashboard` embeds the inspections dashboard (Grafana)
`/analytics/d/dinesafe/dinesafe-inspections?kiosk` in an iframe. Visitors see
it as anonymous Viewers.

- Source: `dinesafe.json`, provisioned from files. UI edits are ephemeral:
  export and commit them to `dinesafe.json`.
- 20 SQL panels, so 20 queries per dashboard load, each capped at 10 seconds.
- Default range: last 90 days. No auto-refresh.
- Every panel filters with `$__timeFilter(inspection_date)`.
- Categories use `COALESCE(infraction_category, infraction_details)`, because
  historical rows have no category.
- Establishment-type panels show historical rows only. Those end on November
  9, 2023, so the panels are empty in the default 90-day range.
- The text panel says establishment type runs to 2023-12-31. That's wrong:
  the data ends on 2023-11-09.
