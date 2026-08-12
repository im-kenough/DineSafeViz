# Monitoring architecture (coming soon)

The monitoring service has two goals:

1. Inform users of the app status.
2. Provide telemetry so that systems administrators can monitor and respond to
   issues.

The monitoring service is a dockerized stack that resides in a VM. It consists
of the following:

- Grafana: metrics aggregation
- An APM tool: app monitoring
- Graylog: centralized logging
- Uptime Kuma: informs users of the service status
- Prometheus and InfluxDB: time series data storage and aggregation
- Alertmanager: rules for alerting
- Discord: alerts are sent to a private Discord channel

TODO: draw a diagram of the monitoring tools.

## Status dashboard

A user-facing status dashboard (Uptime Kuma) shows the health of the following:

1. The web app
2. The DSV analytics dashboard

## Application

Monitor the health of the following:

- The web app
- The database
- DSV metrics

### Metrics

TODO: define the metrics to monitor. Create health check endpoints. Consider
the four golden signals. Create a Grafana dashboard for them.

## Infrastructure

- Monitor VM health.

## Monitoring tools

### Grafana

TODO

### APM tool

TODO

### Graylog

Graylog performs centralized logging for the DineSafeViz application and its
supporting infrastructure. TODO: document where the logs are streamed and
recorded.

### Uptime Kuma

TODO

### InfluxDB

TODO

### Prometheus

Node exporter agents run on all VMs and Docker Compose stacks to collect
metrics for Grafana.

## Alerting tools

Alertmanager rules define thresholds and send alerts to a private Discord
channel.

### Alertmanager

TODO

### Discord

TODO: document the Discord channel.
