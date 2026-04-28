# Journal 12

## 2026-04-27 — Convert infraction detail/observation tables to horizontal bar charts

### Goal
Replace the 6 table panels (panels 17, 18, 22, 23, 27, 28) that show long infraction text with horizontal bar charts. Text was getting cut off in table cells.

### Plan
1. Change panel `type` from `"table"` to `"barchart"`
2. Update SQL to `LEFT(field, 70)` via subquery so labels are readable but grouping is on full text
3. Swap `options` to horizontal barchart config (matching panels 15/16 pattern)
4. Swap `fieldConfig.defaults.custom` to barchart fields (remove table-specific `align`, `cellOptions`, `inspect`)
5. Remove table-only `options` keys (`cellHeight`, `footer`, `showHeader`)

### Panels
- 17: Crucial Infractions by Infraction details
- 18: Crucial Infractions by Inspection Observations
- 22: Significant Infractions by Infraction details
- 23: Significant Infractions by Inspection Observations
- 27: Minor Infractions by Infraction details
- 28: Minor Infractions by Inspection Observations

Colors to preserve:
- Crucial: `#dc2626`
- Significant: `orange`
- Minor: `yellow` (panels 27/28 had inconsistent colors — 27 was orange, 28 was #dc2626; normalized both to yellow)

### Result
All 6 panels converted. SQL uses subquery + LEFT(field, 70) pattern. Dashboard version bumped to 19.
