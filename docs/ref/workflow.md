# Workflow

## Coding standards

- Python: [pep8](https://pypi.org/project/pep8/)
- NASA JPL [coding standards](https://en.wikipedia.org/wiki/The_Power_of_10:_Rules_for_Developing_Safety-Critical_Code#cite_note-JPL-2)
  (aspirational)

## Guidelines

- Definition of done: coming soon.
- Use [semantic versioning](https://semver.org/).
- Use [conventional commits](https://www.conventionalcommits.org/), at least
  for PRs. See the
  [cheat sheet](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13).
- Keep feature branches
  [short-lived](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.scm.2-keep-feature-branches-short-lived.html).
- [Use PRs](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cr.6-initiate-code-reviews-using-pull-requests.html),
  and don't merge directly into `main`.

## Sprint planning

Create a GitHub issue for planned features and fixes. Apply the relevant tags
and milestones.

For the full issue lifecycle, label and milestone conventions, and how to use
the GitHub Projects dashboards, see [project management](project-management.md).

## Sprint execution

### Git strategy (work in progress)

This strategy is based on
[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow).

To set up a release, branch `main` into `dev`.

To implement a feature, follow these steps.

1. Branch off `dev` and create a feature, task, or fix branch.
2. Create a PR and merge into `stg`.
3. Perform validation in `stg`.
4. When all PRs for the sprint are consolidated, merge `stg` into `main`, and
   then create the tag.

## Release and tagging process

For the release process, see [release](../how-to/5-release.md).

> [!NOTE]
> Make sure that at least one PR in the release has a `feature` or
> `enhancement` label, so that the version resolver picks a minor bump
> automatically.

## Practices to avoid

- Don't check in secrets, such as API keys, passwords, or other sensitive data.
- Avoid git submodules for sharing common code.

## Definition of done

Coming soon.

## References

- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [Trunk-based development](https://trunkbaseddevelopment.com/)
- [GitHub Flow branching strategy for multi-account DevOps environments](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/implement-a-github-flow-branching-strategy-for-multi-account-devops-environments.html)
- Static analysis: [F Prime Python development](https://nasa.github.io/fprime/UsersGuide/dev/py-dev.html)
- [NASA NPR 7150.2D, Chapter 4](https://nodis3.gsfc.nasa.gov/displayDir.cfm?Internal_ID=N_PR_7150_002D_&page_name=Chapter4)
