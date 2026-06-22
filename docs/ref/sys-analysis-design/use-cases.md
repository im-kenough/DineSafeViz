# DineSafeViz Use Cases

This document outlines the core use cases for the DineSafeViz application, categorized by the primary actor: the End-User and the Sysadmin. 

## End-User Use Cases

These use cases focus on the primary functionality of the application from a public user's perspective.


### UC-USR-01: View Inspection Data

- An end-user goes to the website
- navigate to the inspection page

### UC-USR-02: View Analytics Dashboard

- An end-user goes to the website
- navigate to the dashboard page

## Sysadmin Use Cases

These operational use cases focus on the infrastructure, reliability, and maintenance of the application.

It is performed by the systems administrator.


### UC-SYS-01: Start Up AKS Cluster

C1: Prod
- The sysadmin starts up the AKS cluster in the prod environment.

C2: Stg
- The sysadmin starts up the AKS cluster in the stg environment.

C3: stg-dr
- The sysadmin starts up the AKS cluster in the stg-dr environment.

C4: prod-dr
- The sysadmin starts up the AKS cluster in the prod-dr environment.


### UC-SYS-02: Shut Down AKS Cluster

C1: Prod
- The sysadmin shuts down the AKS cluster in the prod environment.

C2: Stg
- The sysadmin shuts down the AKS cluster in the stg environment.

C3: stg-dr
- The sysadmin shuts down the AKS cluster in the stg-dr environment.

C4: prod-dr
- The sysadmin shuts down the AKS cluster in the prod-dr environment.


### UC-SYS-03: Deploy Application

C1: Staging
- The sysadmin deploys a new application version to the staging environment for integration testing and QA.

C2: Production
- The sysadmin promotes a verified build from staging to the production environment with minimal downtime.


### UC-SYS-04: Refresh Database Data

- The sysadmin (or an automated system) pulls the latest open data from the Toronto Public Health API and updates the application database safely.


### UC-SYS-05: Manage Database Backups

C1: Backup
- The system automatically executes a routine snapshot of the database to ensure data can be recovered.

C2: Restore
- The sysadmin restores the application database from a previous snapshot to recover from data corruption or loss.


### UC-SYS-06: Roll Back Deployment

C1: Production
- The sysadmin reverts the production application to the previous known-good version following a failed deployment or critical bug discovery.

C2: Staging
- The sysadmin reverts the production application to the previous known-good version following a failed deployment or critical bug discovery.

### UC-SYS-07: Rotate Secrets

- The sysadmin securely rotates application secrets and database credentials without causing system downtime.


### UC-SYS-08: Failover to Disaster Recovery (DR)

C1: Production
- The sysadmin provisions AKS for the prod-dr region.
- Performs cut-off activities to route data to the prod-dr environment.

C2: Staging
- The sysadmin provisions AKS for the stg-dr region.
- Performs cut-off activities to route data to the stg-dr environment.


### UC-SYS-09: Failback to Primary Environment

C1: Production (Primary infrastructure intact)
- The sysadmin performs cut-off activities to route data back to the primary region.
- Tears down the AKS cluster in the prod-dr region.

C2: Production (Primary infrastructure requires redeployment)
- The sysadmin provisions the primary AKS cluster.
- Performs cut-off activities to route data back.
- Tears down the AKS cluster in the prod-dr region.

C3: Staging
- The sysadmin tears down the AKS cluster in the stg-dr region.
- Performs cut-off activities to route data back to the standard Staging environment.
