# Development process

This document describes how DineSafeViz plans, builds, and ships work: coding
standards, contribution guidelines, sprint execution, and project management.

## Coding standards

- Python: [pep8](https://pypi.org/project/pep8/)
- NASA JPL [coding standards](https://en.wikipedia.org/wiki/The_Power_of_10:_Rules_for_Developing_Safety-Critical_Code#cite_note-JPL-2)
  (aspirational)
- Static analysis: [F Prime Python development](https://nasa.github.io/fprime/UsersGuide/dev/py-dev.html)
- [NASA NPR 7150.2D, Chapter 4](https://nodis3.gsfc.nasa.gov/displayDir.cfm?Internal_ID=N_PR_7150_002D_&page_name=Chapter4)

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

### Practices to avoid

- Don't check in secrets, such as API keys, passwords, or other sensitive data.
- Avoid git submodules for sharing common code.

## Sprint planning and execution

Create a GitHub issue for planned features and fixes. Apply the relevant tags
and milestones. For the full issue lifecycle, label and milestone
conventions, and how to use the GitHub Projects dashboards, see
[project management](#project-management).

### Git strategy (work in progress)

This strategy is based on
[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow).

To set up a release, branch `main` into `dev`. To implement a feature,
follow these steps.

1. Branch off `dev` and create a feature, task, or fix branch.
2. Create a PR and merge into `stg`.
3. Perform validation in `stg`.
4. When all PRs for the sprint are consolidated, merge `stg` into `main`, and
   then create the tag.

### Release and tagging process

For the release process, see [release](../how-to/6-release.md).

> [!NOTE]
> Make sure that at least one PR in the release has a `feature` or
> `enhancement` label, so that the version resolver picks a minor bump
> automatically.

### References

- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [Trunk-based development](https://trunkbaseddevelopment.com/)
- [GitHub Flow branching strategy for multi-account DevOps environments](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/implement-a-github-flow-branching-strategy-for-multi-account-devops-environments.html)

## Project management

DineSafeViz uses GitHub Issues and GitHub Projects to plan and track all
work. Releases are organized by version (v0.1.0, v0.2.0, and so on) rather
than by time-boxed sprints. Work moves through a defined lifecycle, from a
captured idea to a scheduled issue to a completed task.

### Projects

Two GitHub Projects dashboards support the workflow.

**[DineSafeViz Project Management](https://github.com/users/im-kenough/projects/6)**
is the complete work tracker. It contains every issue across all releases —
historical, active, and backlog. Use the milestone filter to scope the view to
a specific version. This is the primary day-to-day board.

**[DSV-roadmap](https://github.com/users/im-kenough/projects/11)** is the
forward-looking release plan. It shows what's coming across all planned
versions and what's captured but not yet scheduled (`vNext`). Use this to
understand sequencing and priorities at a glance.

### Issue lifecycle

Every issue moves through the following stages before it closes.

```
Captured (idea/question)
        ↓
   Committed (vNext)
        ↓
  Scheduled (v0.x.0)
        ↓
 In progress → Done
```

**Captured** issues are things worth remembering but not yet committed to.
They carry an `idea` or `question` label and have no milestone. They sit in
the backlog until a planning decision is made.

**Committed** issues are things you've decided to build but haven't assigned
to a release yet. They belong to the `vNext` milestone. When you start
planning a new release, you promote issues from `vNext` into the target
version milestone.

**Scheduled** issues belong to a specific version milestone (for example,
`v0.3.0`). They're active work with a defined release target.

**Done** issues close after their PR merges. They stay in the project board
as a permanent record of what shipped in each release.

### Labels

Labels describe the nature of an issue. Multiple labels can apply to a single
issue.

#### Status labels

These labels indicate an issue's planning state. They only apply before an
issue has a milestone.

| Label | Meaning |
|---|---|
| `idea` | Bookmark or speculative item. Not committed to implementing. |
| `question` | Open strategic question with no clear answer yet. For example, "What cloud provider should I expand to first?" |

#### Domain labels

These labels describe what area of the system an issue touches.

| Label | Area |
|---|---|
| `ui` | Frontend and visualization |
| `db` | Database operations |
| `infra` | Infrastructure setup and configuration |
| `iac` | Infrastructure as code |
| `ops` | Operational concerns: scaling, health, observability |
| `infosec` | Security, IAM, secrets management |
| `ci-cd` | CI/CD pipelines and release management |
| `dr` | Disaster recovery and resiliency |
| `perf` | Performance enhancements |
| `build` | Build systems and dependencies |
| `documentation` | Documentation additions or updates |
| `chore` | Routine maintenance tasks |
| `refactor` | Code changes that don't add features or fix bugs |
| `bug` | Something isn't working |
| `enhancement` | New feature or improvement |

### Milestones

Milestones map directly to release versions. Every committed issue belongs to
exactly one milestone.

| Milestone | Meaning |
|---|---|
| `v0.1.0`, `v0.2.0`, ... | Specific release version. Issues here are scheduled. |
| `vNext` | Committed for implementation, but not yet assigned to a specific version. |

Issues with no milestone are unscheduled ideas or open questions. They carry
an `idea` or `question` label.

### Day-to-day usage

#### Starting work on a release

1. Open the [project management board](https://github.com/users/im-kenough/projects/6).
2. Filter by the current milestone. Type `milestone:v0.3.0` in the filter bar.
3. Review what's in **Backlog**. Move issues to **Ready** as you confirm scope.
4. Pick up an issue. Move it to **In progress**.
5. Open a branch, do the work, and open a PR.
6. When the PR merges and the issue closes, move it to **Done**.

#### Promoting an idea to committed work

1. Find the issue. Filter by `label:idea` or `label:question`.
2. Decide it's worth doing.
3. Remove the `idea` or `question` label.
4. Set the milestone to `vNext`.
5. The issue now appears in the roadmap as committed but unscheduled.

#### Planning a new release

1. Open the [roadmap](https://github.com/users/im-kenough/projects/11).
2. Filter by `milestone:vNext` to see all committed, unscheduled issues.
3. Decide which ones belong in the next release.
4. On each issue, change the milestone from `vNext` to the new version (for
   example, `v0.4.0`).
5. The issue moves out of `vNext` and into the scheduled release.

#### Looking back at a previous release

1. Open the [project management board](https://github.com/users/im-kenough/projects/6).
2. Filter by the version. For example, `milestone:v0.1.0`.
3. All issues from that release appear with their final status.

### Status values

Issues on the project board move left to right through the following
statuses.

| Status | Meaning |
|---|---|
| **Backlog** | Scheduled for this release but not started. |
| **Ready** | Scope confirmed, ready to pick up. |
| **In progress** | Actively being worked on. |
| **In review** | PR open, awaiting review or CI. |
| **Done** | Merged and closed. |
