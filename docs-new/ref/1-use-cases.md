# DineSafeViz use cases

This document outlines the core use cases for the DineSafeViz application,
grouped by primary actors.

## End-user use cases

### UC-USR-01: View inspection data

- The end user goes to the website.
- The end user navigates to the inspection page.

### UC-USR-02: View inspections dashboard

- The end user goes to the website.
- The end user navigates to the inspections dashboard (Grafana) page.

## Sysadmin use cases

These operational use cases focus on the infrastructure, reliability, and
maintenance of the application. The systems administrator performs them.

### UC-SYS-01: Create and delete the stg VM

Stg is billed pay-as-you-go, so it exists only while you're testing.

- C1 (create): the sysadmin creates `vm-dsv-stg01` and runs its first deploy.
- C2 (delete): the sysadmin deletes `vm-dsv-stg01` and its public IP address
  when testing is done. The identity, vault, network, and tunnel stay.

### UC-SYS-02: Deploy the application

Deploys run `scripts/deploy.sh` on the VM. The stack restarts, so the site is
unavailable for a short time during each deploy.

- C1 (stg): the sysadmin deploys the latest `main` to stg for testing.
- C2 (prod): the sysadmin takes an OS disk snapshot, and then deploys a
  release tag (`vX.Y.Z`) that was verified on stg to prod.

### UC-SYS-03: Refresh the database data

- C1 (scheduled): a systemd timer runs the pipeline on weekday mornings. It
  copies new open data from Toronto Open Data to the Blob raw zone, and then
  loads the newest file into the database.
- C2 (manual): the sysadmin runs `scripts/pipeline.sh` to ingest or reload
  data on demand.

### UC-SYS-04: Manage the prod backups

Backups are incremental snapshots of the prod VM's OS disk. Stg has no
backups. Its data can be reloaded from the Blob raw zone.

- C1 (backup): the sysadmin takes a snapshot before every prod deploy and
  keeps the newest three.
- C2 (restore): the sysadmin creates a disk from a snapshot and swaps it in as
  the prod VM's OS disk to recover from data corruption or loss.

### UC-SYS-05: Roll back a deployment

- C1 (prod): the sysadmin redeploys the previous release tag. If the failed
  release changed the database, the sysadmin restores the pre-deploy
  snapshot instead.
- C2 (stg): the sysadmin reverts the bad commit on `main` and redeploys stg.

### UC-SYS-06: Rotate secrets

- The sysadmin rotates a secret in Key Vault, applies it on the VM, and then
  redeploys. The app has a short outage while the containers restart, and it
  can't open new database connections until the redeploy finishes.

## Deferred use cases

These use cases need the planned AKS architecture and are out of scope for
the VM phase.

- Fail over to a disaster recovery (DR) region.
- Fail back to the primary region.
- Start up and shut down an AKS cluster.
- Deploy with minimal or zero downtime.
- Rotate secrets without downtime.
- Run automated, scheduled database backups.
