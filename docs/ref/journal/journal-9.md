# Journal 9 — Grafana Dashboard Design

## 2026-04-26 16:00
**Explored project context for Grafana dashboard brainstorm**

- Dataset: ~18,380 rows of Toronto DineSafe food inspections (Nov 2023 – late 2025, with a few 2026 entries)
- Schema: `inspections` table with columns: establishment_id, inspection_id, establishment_name, establishment_type, establishment_address, infraction_details, inspection_observation, inspection_date, severity, action, outcome, outcome_date, amount_fined, latitude, longitude, unique_id
- Severity values: C - Crucial, S - Significant, M - Minor, NA, None
- Action values: Notice to Comply, Summons, Ticket, Warning Letter, Prohibition Order Requested, Summons and Health Hazard Order, Corrected During Inspection, Not in Compliance, None
- Outcome values: Pending, Cancelled, Charges Withdrawn, Conviction - Fined, Conviction: Fined, Corrected During Inspection, Notice to Comply, Not in Compliance, None
- Establishment types: many (Restaurant, Food Take Out, Bakery, Supermarket, etc.) — CSV has messy data with some types parsed from names
- Current app: Flask + Postgres, served on port 5000, shows inspections grouped by date within year/quarter selectors
- Docker: postgres:17.9 + Flask web container, docker-compose with dsv-db-data volume
