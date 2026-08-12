# Monitoring Architecture - Coming Soon (TM)

The goal of the monitoring service will be to 1. Inform users of the app status 2. Provide telemetry for systems administrators to monitor and respond to issues

The monitoring service is a dockerized stack that resides in a VM made up of:
- Grafana: metrics aggregation
- Some kind of APM tool: app monitoring
- Graylog: centeralized logging
- Uptime Kuma: informs user of service status
- Prometheus, InfluxDB: time series data storage and aggregation
- Alert Manager: rules for alerting
- Discord: alerts are sent to a private discord channel

Draw a diagram of the monitoring tools.

## Status Dashboard

A status dashboard (uptime kuma) is user facing. It shows the health of 1. the web app 2. the DSV analytics dashboard

## Application

Monitor the health of:

- the webapp
- db
- dsv metrics

### Metrics

Define metrics to monitor on. Create health check endpoints. 4 Golden Signals? Create a grafana dashboard for it

## Infrastructure

- monitor vm health


## Monitoring tools

### Grafana


### Something for APM

### Graylog

Performs centralized logging for the DineSaveViz application and its supporting infrastructure.

Logs are streamed and recorded to X.

### Uptime Kuma

### InfluxDB

### Prometheus

Node exporter agents are installed on all VMs and docker compose stacks to collect metrics for grafana

## Alerting tools

Alert Manager rules define thresholds and send alerts to a private Discord channel

## Alert Manager

## Discord

Discord channel info