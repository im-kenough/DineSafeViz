# Tech Stack

Phases of the [DevOps lifecycle](https://www.ibm.com/think/topics/devops-lifecycle)

# Plan

 In this stage, teams identify the business requirement and collect end-user feedback. They create a project roadmap to maximize the business value and deliver the desired product during this stage.

 - Project roadmap: github projects
 - requirements gathering: github issues

# Code

Create working source code

- IDE: VSCode
- Software versioning: git
- Source COde Management: github

# Build
Compile, validate and package source code into deployable artifacts.

- Building locally using docker desktop
  - automated scripts are used to seed the database and build the app

# Test
Validate code behaves as expected

- Testing: pytest for unit tests

# Release
Final quality and security checks. Coordianting how to move into staging and production environments

- Github actions


# Deploy
Delivering code automatically to the target environment

- Configuration Management: Comming Soon(™️)
- Infrastructure as Code: Comming Soon(™️)
- Release drafter: publish a deployable release

# Operate
Keeping live system stable, performance, secure and available

- App deployed to a linux VM in self hosted proxmox environment

# Monitor
Observe Applications & infrastrucutre in production to detect issues

- Monitor VM & app in grafana: Comming Soon(™️)
- Centralized logging: Comming Soon(™️)
