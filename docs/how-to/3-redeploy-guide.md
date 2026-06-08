# Redeploy Guide

This document provides instructions on how to redeploy the application to existing infrastructure.

There are several redeployment use cases

## Case 1

Scenario: 
  - You want to:
    - Redeploy the latest code changes to the running instance.
    - Keep existing docker volumes

```bash
make redeploy-app-keep-data
```
- destroys app, keeps docker volumes
- reclones repo, templates .env, docker compose up

## Case 2

Scenario: 
  - You want to:
    - Redeploy the latest code changes to the running instance.
    - Delete existing docker volumes to trigger a fresh initialization

```bash
make redeploy-app
```
## Case 3

Scenario: 
  - You want to:
    - Redeploy the latest code changes to a brand new instance

```bash
make down && make up
```
This will delete the app and VM, then provision another VM and deploy the app.