# Workflow

## Sprint planning

Create a github issue for planned features and fixes. Apply relevant tags and milestones

## Sprint execution

Setting up a release:

1. branch main into dev

Implementing features:

1. branch off dev and create a feature/task/fix branch
2. create a PR and merge into stg
3. perform validation in stg
4. when all PRs for the sprint are consolidated:
   - merge stg into main
   - create tag