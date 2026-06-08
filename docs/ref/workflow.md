# Workflow

## Coding Standards

- Python: [pep8](https://pypi.org/project/pep8/)
- NASA JPL [coding standards](https://en.wikipedia.org/wiki/The_Power_of_10:_Rules_for_Developing_Safety-Critical_Code#cite_note-JPL-2) - aspirational

## Guidelines

- Definition of Done - Coming Soon (™️)
- Use [semantic versioning](https://semver.org/)
- Use [conventional commits](https://www.conventionalcommits.org/), at least for PRs.[cheat sheet](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13)
- Keep feature branches [short lived](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.scm.2-keep-feature-branches-short-lived.html)
- [Use PRs](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cr.6-initiate-code-reviews-using-pull-requests.html) and don't directly merge into `main`

## Sprint planning

Create a github issue for planned features and fixes. Apply relevant tags and milestones

See [Project management](project-management.md) for the full issue lifecycle,
label and milestone conventions, and how to use the GitHub Projects dashboards.

## Sprint execution

### Git Strategy - WIP

Looking at [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)

Setting up a release:

1. branch main into dev

Implementing features:

1. branch off dev and create a feature/task/fix branch
2. create a PR and merge into stg
3. perform validation in stg
4. when all PRs for the sprint are consolidated:
   - merge stg into main
   - create tag

## Release & tagging process

[Release](docs/how-to/5-release.md) process. 

> [!NOTE]
> Ensure at least one PR in the release has a `feature` or `enhancement` label so version resolver picks a minor bump automatically.

## Antipatterns

- Don't check in secrets (sensitive data like API keys, password or secrets)
- Avoid using gitsubmodules for sharing common code
- 
## Definition of Done

Coming Soon(TM)

## Miscellaneous

https://docs.github.com/en/get-started/using-github/github-flow
https://trunkbaseddevelopment.com/

https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/implement-a-github-flow-branching-strategy-for-multi-account-devops-environments.html

Static analysis
https://nasa.github.io/fprime/UsersGuide/dev/py-dev.html

https://nodis3.gsfc.nasa.gov/displayDir.cfm?Internal_ID=N_PR_7150_002D_&page_name=Chapter4
