# DineSafe colours

DineSafeViz uses the colours from Toronto Public Health's official DineSafe
notice signs. The hex values were sampled from the most common colour in each
sign image in `src/dsv-app/static/imgs/`.

## Colour values

Each colour marks one inspection status and the infraction severity that
leads to it.

| Token               | Hex       | Inspection status | Infraction severity |
| ------------------- | --------- | ----------------- | ------------------- |
| `--dinesafe-green`  | `#00875F` | Pass              | Minor               |
| `--dinesafe-yellow` | `#FBEF45` | Conditional Pass  | Significant         |
| `--dinesafe-red`    | `#F04B45` | Closed            | Crucial             |

## Where the colours are defined

The colours live in two places, because the Grafana dashboard can't read CSS
variables.

- `src/dsv-app/static/style.css`: the `--dinesafe-*` tokens in `:root`.
- `src/dsv-analytics/provisioning/dashboards/dinesafe.json`: hard-coded hex
  values on the Pass, Conditional Pass, and Closed panels.

<!-- prettier-ignore -->
> [!IMPORTANT]
> If you change a colour, you must update both files.
> `test_dashboard_status_colours_match_css` in
> `src/dsv-app/tests/test_dashboard.py` fails when they drift apart.
