# Journal 43

## 2026-05-09 — Fix merge conflicts in PR #100 (stg → main)

**Task:** Resolve merge conflicts in PR #100 so that stg overwrites main everywhere.

**Analysis:**
- PR #100: `stg` (head) → `main` (base), state CONFLICTING
- Common ancestor: `a85c1e2`
- `origin/main` has 2 commits not in `stg`: `55cac5f` (deploy basic web app) and `cfd0d90` (bump requests)
- `origin/stg` has ~30+ commits not in `main`
- User wants stg to win all conflicts

**Decision:** Merge `origin/main` into `stg` using `-X ours` strategy (stg's version wins). This creates a merge commit on stg, making the PR cleanly mergeable without touching main directly.
