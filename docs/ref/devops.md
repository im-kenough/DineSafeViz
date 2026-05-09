# Tech Stack

Phases of the [DevOps lifecycle](https://www.ibm.com/think/topics/devops-lifecycle)

# Plan

Define requirements, create roadmaps, and organize tasks

- [Github Issues](https://github.com/im-kenough/DineSafeViz/issues): identify issues, gathering feedback
- [Github Projects](https://github.com/users/im-kenough/projects/6): Backlog management, sprint planning, user story creation.

# Code

Create working source code

- IDE: VSCode
  - insert list of useful extensions & linting tools
  - Developed with assistance of Agentic coding: Claude Code, Codex, Gemini CLI
- Software versioning: git
- Source COde Management: [github](https://github.com/im-kenough/DineSafeViz). Talk about branching strategy.

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
