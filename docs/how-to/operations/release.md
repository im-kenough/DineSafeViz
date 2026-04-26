# Release Process

This document describes how to release new versions of the script.

## Automation Overview

The project uses GitHub Actions to automate the release process:
- **Release Drafter**: Automatically drafts release notes based on Pull Request labels (e.g., `feature`, `bug`).
- **GitHub Release**: Automatically creates a formal GitHub Release whenever a version tag (e.g., `v1.0.0`) is pushed to the repository.

## How to Release v1.0.0

To designate the current state as v1.0.0:

1. **Ensure all changes are merged** into the `main` branch.
2. **Create a git tag**:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   ```
3. **Push the tag**:
   ```bash
   git push origin v1.0.0
   ```
4. **Verify**: Check the "Releases" section on GitHub. The automation will have created a new release with automated change notes.

## Future Releases (SemVer)

This project follows [Semantic Versioning](https://semver.org/):
- **Major** (x.0.0): Breaking changes.
- **Minor** (0.x.0): New features (backward compatible).
- **Patch** (0.0.x): Bug fixes (backward compatible).

### Workflow for Future Changes

1. **Use Branching/PRs**: Make changes on feature branches.
2. **Label Pull Requests**: Apply labels like `feature`, `bug`, `major`, or `fix` to your PRs. This helps the Release Drafter categorize the changes.
3. **Merge to Main**: Once the PR is merged, the Release Drafter will update a "Draft" release.
4. **Publish**: When ready to release, follow the tagging steps above with the next version number.
