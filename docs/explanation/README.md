# Explanation

Understanding-oriented discussion of how DineSafeViz is designed and why.

1. [Use cases](1-use-cases.md)
2. [Application architecture](2-application-architecture.md)
3. [Data architecture](3-data-architecture.md)
4. [Infrastructure as code](4-infrastructure-as-code.md)
5. [Network architecture](5-network-architecture.md)
6. [Security architecture](6-security-architecture.md)
7. [CI/CD architecture](7-ci-cd-architecture.md)
8. [Disaster recovery and resiliency](8-disaster-recovery.md)
9. [Monitoring architecture](9-monitoring-architecture.md)
10. [Testing architecture](10-testing-architecture.md)
11. [Development process](11-development-process.md)

---

# Tech stack

The following sections map the tools to the phases of the
[DevOps lifecycle](https://www.ibm.com/think/topics/devops-lifecycle).

## Plan

Define requirements, create roadmaps, and organize tasks.

- [GitHub Issues](https://github.com/im-kenough/DineSafeViz/issues): identify
  issues and gather feedback.
- [GitHub Projects](https://github.com/users/im-kenough/projects/6): backlog
  management, sprint planning, and user story creation.

## Code

Create working source code.

- IDE: VS Code.
  - TODO: list the useful extensions and linting tools.
  - Developed with the assistance of agentic coding: Claude Code, Codex, and
    Gemini CLI. Spend limits are enforced.
- Software versioning: git.
- Source code management:
  [GitHub](https://github.com/im-kenough/DineSafeViz). TODO: describe the
  branching strategy.

## Build

Compile, validate, and package the source code into deployable artifacts.

- Build locally using Docker Desktop.
  - Automated scripts seed the database and build the app.

## Test

Validate that the code behaves as expected.

- Testing: pytest for unit tests.

## Release

Run the final quality and security checks. Coordinate how to move into the
staging and production environments.

- GitHub Actions.
  - [SBOM generation](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.scm.10-generate-a-comprehensive-software-inventory-for-each-build.html)
    for releases: coming soon.

## Deploy

Deliver the code automatically to the target environment.

- Configuration management: coming soon.
- Infrastructure as code: coming soon.
- Release Drafter: publish a deployable release.

## Operate

Keep the live system stable, performant, secure, and available.

- App deployed to a Linux VM in a self-hosted Proxmox environment.

## Monitor

Observe the application and infrastructure in production to detect issues.

- Monitor the VM and app in Grafana: coming soon.
- Centralized logging: coming soon.
