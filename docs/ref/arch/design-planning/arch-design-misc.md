# Architecture Design - Miscellaneous

This document contains miscellaneous design decisions.

## Domain Name

- Purchased dinesafeviz.com
- Would be nice to also buy dinesafeviz.ca for completeness since it's a Toronto centric website and redirect it to dinesafeviz.com, but not doing it for cost reasons.

## Disaster Recovery

### Holding page

Decision:
When the cluster is unavailable, a holding page giving an offline tour will be served.

Selection:
- Going with manual DNS flip

Considerations:

- The proper azure way of doing this is to use Azure front door to to make load balancing decisions to serve the holding page
  - Don't want to pay $35 usd/mth + egress fees
- Cheaper architecture is Cloudflare Load Balancing. Performs health checks and routes appropriately
  - Still don't want to pay $10-$15/mth
- Manual DNS cutover is free. Wrap it in a Github action.