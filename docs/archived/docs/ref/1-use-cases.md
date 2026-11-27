# DineSafeViz use cases

This document outlines the core use cases for the DineSafeViz application,
grouped by the primary actor: the end user and the sysadmin.

## End-user use cases

These use cases focus on the primary functionality of the application from a
public user's perspective.

### UC-USR-01: View inspection data

- The end user goes to the website.
- The end user navigates to the inspection page.

### UC-USR-02: View analytics dashboard

- The end user goes to the website.
- The end user navigates to the dashboard page.

## Sysadmin use cases

These operational use cases focus on the infrastructure, reliability, and
maintenance of the application. The systems administrator performs them.

### UC-SYS-01: Start up the AKS cluster

- C1 (prod): the sysadmin starts up the AKS cluster in the prod environment.
- C2 (stg): the sysadmin starts up the AKS cluster in the stg environment.
- C3 (stg-dr): the sysadmin starts up the AKS cluster in the stg-dr
  environment.
- C4 (prod-dr): the sysadmin starts up the AKS cluster in the prod-dr
  environment.

### UC-SYS-02: Shut down the AKS cluster

- C1 (prod): the sysadmin shuts down the AKS cluster in the prod environment.
- C2 (stg): the sysadmin shuts down the AKS cluster in the stg environment.
- C3 (stg-dr): the sysadmin shuts down the AKS cluster in the stg-dr
  environment.
- C4 (prod-dr): the sysadmin shuts down the AKS cluster in the prod-dr
  environment.

### UC-SYS-03: Deploy the application

- C1 (staging): the sysadmin deploys a new application version to the staging
  environment for integration testing and QA.
- C2 (production): the sysadmin promotes a verified build from staging to the
  production environment with minimal downtime.

### UC-SYS-04: Refresh the database data

- The sysadmin (or an automated system) pulls the latest open data from the
  Toronto Public Health API and updates the application database safely.

### UC-SYS-05: Manage the database backups

- C1 (backup): the system automatically runs a routine snapshot of the database
  so that the data can be recovered.
- C2 (restore): the sysadmin restores the application database from a previous
  snapshot to recover from data corruption or loss.

### UC-SYS-06: Roll back a deployment

- C1 (production): the sysadmin reverts the production application to the
  previous known-good version after a failed deployment or a critical bug.
- C2 (staging): the sysadmin reverts the staging application to the previous
  known-good version after a failed deployment or a critical bug.

### UC-SYS-07: Rotate secrets

- The sysadmin rotates the application secrets and database credentials securely
  without causing system downtime.

### UC-SYS-08: Fail over to disaster recovery (DR)

- C1 (production): the sysadmin provisions AKS for the prod-dr region, and then
  performs cutover activities to route data to the prod-dr environment.
- C2 (staging): the sysadmin provisions AKS for the stg-dr region, and then
  performs cutover activities to route data to the stg-dr environment.

### UC-SYS-09: Fail back to the primary environment

- C1 (production, primary infrastructure intact): the sysadmin performs cutover
  activities to route data back to the primary region, and then tears down the
  AKS cluster in the prod-dr region.
- C2 (production, primary infrastructure requires redeployment): the sysadmin
  provisions the primary AKS cluster, performs cutover activities to route data
  back, and then tears down the AKS cluster in the prod-dr region.
- C3 (staging): the sysadmin tears down the AKS cluster in the stg-dr region,
  and then performs cutover activities to route data back to the standard
  staging environment.
