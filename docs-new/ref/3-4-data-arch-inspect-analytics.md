# Inspection Analytics

### Grafana dashboard

`/dashboard` embeds the Grafana dashboard
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
