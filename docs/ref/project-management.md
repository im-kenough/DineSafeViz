# Project management

DineSafeViz uses GitHub Issues and GitHub Projects to plan and track all work.
Releases are organized by version (v0.1.0, v0.2.0, and so on) rather than by
time-boxed sprints. Work is promoted through a defined lifecycle — from a
captured idea to a scheduled issue to a completed task.

## Projects

Two GitHub Projects dashboards support the workflow.

**[DineSafeViz Project Management](https://github.com/users/im-kenough/projects/6)**
is the complete work tracker. It contains every issue across all releases —
historical, active, and backlog. Use the milestone filter to scope the view to
a specific version. This is the primary day-to-day board.

**[DSV-roadmap](https://github.com/users/im-kenough/projects/11)** is the
forward-looking release plan. It shows what's coming across all planned versions
and what's captured but not yet scheduled (`vNext`). Use this to understand
sequencing and priorities at a glance.

## Issue lifecycle

Every issue moves through the following stages before it's closed.

```
Captured (idea/question)
        ↓
   Committed (vNext)
        ↓
  Scheduled (v0.x.0)
        ↓
 In progress → Done
```

**Captured** issues are things worth remembering but not yet committed to. They
carry an `idea` or `question` label and have no milestone. They sit in the
backlog until a planning decision is made.

**Committed** issues are things you've decided to build but haven't assigned to
a release yet. They belong to the `vNext` milestone. When you start planning a
new release, you promote issues from `vNext` into the target version milestone.

**Scheduled** issues belong to a specific version milestone (for example,
`v0.3.0`). They're active work with a defined release target.

**Done** issues are closed after their PR merges. They stay in the project
board as a permanent record of what shipped in each release.

## Labels

Labels describe the nature of an issue. Multiple labels can apply to a single
issue.

### Status labels

These labels indicate an issue's planning state. They're only applied before
an issue has a milestone.

| Label | Meaning |
|---|---|
| `idea` | Bookmark or speculative item. Not committed to implementing. |
| `question` | Open strategic question with no clear answer yet. For example, "What cloud provider should I expand to first?" |

### Domain labels

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

## Milestones

Milestones map directly to release versions. Every committed issue belongs to
exactly one milestone.

| Milestone | Meaning |
|---|---|
| `v0.1.0`, `v0.2.0`, ... | Specific release version. Issues here are scheduled. |
| `vNext` | Committed for implementation, but not yet assigned to a specific version. |

Issues with no milestone are unscheduled ideas or open questions. They carry
an `idea` or `question` label.

## Day-to-day usage

### Starting work on a release

1. Open the [project management board](https://github.com/users/im-kenough/projects/6).
2. Filter by the current milestone — type `milestone:v0.3.0` in the filter bar.
3. Review what's in **Backlog**. Move issues to **Ready** as you confirm scope.
4. Pick up an issue: move it to **In progress**.
5. Open a branch, do the work, open a PR.
6. When the PR is merged and the issue closes, move it to **Done**.

### Promoting an idea to committed work

1. Find the issue (filter by `label:idea` or `label:question`).
2. Decide it's worth doing.
3. Remove the `idea` or `question` label.
4. Set the milestone to `vNext`.
5. The issue now appears in the roadmap as committed but unscheduled.

### Planning a new release

1. Open the [roadmap](https://github.com/users/im-kenough/projects/11).
2. Filter by `milestone:vNext` to see all committed, unscheduled issues.
3. Decide which ones belong in the next release.
4. On each issue, change the milestone from `vNext` to the new version (for
   example, `v0.4.0`).
5. The issue moves out of `vNext` and into the scheduled release.

### Looking back at a previous release

1. Open the [project management board](https://github.com/users/im-kenough/projects/6).
2. Filter by the version — for example, `milestone:v0.1.0`.
3. All issues from that release appear with their final status.

## Status values

Issues on the project board move left to right through the following statuses.

| Status | Meaning |
|---|---|
| **Backlog** | Scheduled for this release but not started. |
| **Ready** | Scope confirmed, ready to pick up. |
| **In progress** | Actively being worked on. |
| **In review** | PR open, awaiting review or CI. |
| **Done** | Merged and closed. |
