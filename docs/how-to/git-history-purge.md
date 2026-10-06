# Purge the old CSVs from git history

This runbook removes the DineSafe CSVs from every commit in the repository,
so new clones no longer download data that now lives in Azure Blob Storage.
The CSVs are about 240 MB uncompressed, and they make up about 30 MiB of the
34 MiB pack. It also removes a Terraform provider binary and state
file that were committed by mistake. You run it once, by hand, after these
files are gone from `main`.

<!-- prettier-ignore -->
> [!CAUTION]
> This rewrites history. Every commit SHA from the first CSV commit onward
> changes, and every existing clone, fork, and open pull request stops
> matching GitHub. Read the whole runbook before you start.

## Before you start

This section lists what the rewrite changes and what must be true first.

The rewrite changes the following:

- Every commit SHA after the first commit that added a CSV, which was in June
  2026. Release tags move to the rewritten commits.
- `sha-<commit>` image tags in GHCR no longer match any commit. Images
  already deployed keep running, but the next deploy waits for `images.yml`
  to build the rewritten commit.
- Open pull requests break, so merge or close them first.
- Every clone must be replaced with a fresh clone, including both VMs.

Confirm these prerequisites:

- The pull request that removed the CSV folders and stopped tracking
  `infra/rug/terraform/.terraform` and `terraform.tfstate` is merged, and
  prod loads its data from Blob Storage.
- There are no open pull requests.
- `git filter-repo` is installed on your workstation. On Ubuntu, run
  `sudo apt-get install git-filter-repo`.
- You have a few minutes when no one, including GitHub Actions, pushes to
  the repository.

## Back up the repository

A mirror clone holds every branch, tag, and ref, so you can restore the
repository exactly if something goes wrong. Keep it until you've verified the
result.

```bash
cd ~
git clone --mirror git@github.com:im-kenough/DineSafeViz.git dsv-backup.git
```

## Rewrite the history

Run the rewrite in a second, fresh mirror clone, never in your working clone.
`git filter-repo` refuses to run in a clone that isn't fresh.

1.  Make the fresh mirror clone and record its size:

    ```bash
    cd ~
    git clone --mirror git@github.com:im-kenough/DineSafeViz.git dsv-purge.git
    cd dsv-purge.git
    git count-objects -vH | grep size-pack
    ```

2.  Remove the files from every commit. The list includes every path a CSV
    has had, including folders that were later moved. Git stores identical
    contents once, so if one old path is left out, its CSVs stay in the
    history under that path and the repository barely shrinks.

    ```bash
    git filter-repo --invert-paths \
      --path src/data \
      --path src/db/Dinesafe.csv \
      --path db/Dinesafe.csv \
      --path docs/ref/local-data \
      --path docs/rug/0-needs-review/ref/local-data \
      --path docs/0-needs-review/ref/local-data \
      --path infra/rug/terraform/.terraform \
      --path infra/rug/terraform/terraform.tfstate
    ```

3.  Record the new size. It drops from about 34 MiB to under 4 MiB:

    ```bash
    git count-objects -vH | grep size-pack
    ```

## Push the rewritten history

`git filter-repo` removes the `origin` remote so you can't push by accident.
Add it back, then force-push every branch and tag.

1.  In GitHub, go to **Settings** > **Branches** (or **Rules** >
    **Rulesets**). Temporarily allow force pushes to `main` for your
    account.
2.  Push:

    ```bash
    git remote add origin git@github.com:im-kenough/DineSafeViz.git
    git push --force --mirror origin
    ```

    GitHub rejects updates to `refs/pull/*`, so the output lists those refs
    as `! [remote rejected]`. That's expected. The next section covers them.
3.  Turn force-push protection on `main` back on.

## Re-clone on each VM

Each VM's clone still holds the old history and its CSVs. Replace
the clone and keep the two files that aren't in git.

The rewritten commits have new SHAs, so stg's `sha-<commit>` images don't
exist yet. Before you deploy stg, wait until `images.yml` finishes on the
rewritten `main`. Prod deploys use version tags such as `0.5.0`, which don't
change, so prod can deploy right away.

On each VM, run the following, with `stg` or `prod` as the environment:

```bash
cd ~
mv DineSafeViz DineSafeViz.old
git clone https://github.com/im-kenough/DineSafeViz.git DineSafeViz
cp DineSafeViz.old/deploy/stg.env DineSafeViz/deploy/
cp -a DineSafeViz.old/data DineSafeViz/
cd DineSafeViz
./scripts/deploy.sh stg main          # prod: ./scripts/deploy.sh prod vX.Y.Z
```

When the deploy succeeds, remove `~/DineSafeViz.old`. The systemd units point
at `~/DineSafeViz`, so they keep working without changes.

Replace your own working clone the same way: clone fresh, and copy over
`.env` and `data/` if you use them.

## What stays on GitHub

The rewrite achieves its goal, smaller clones, as soon as the push finishes:
a new clone fetches only branches and tags. The old commits still exist on
GitHub, though, and you can't remove them yourself.

- **Pull request refs.** `refs/pull/*` are read-only, so closed pull requests
  still point at the old commits, and their pages still show them.
- **Cached views.** Anyone who knows an old commit SHA can still open it.

Only GitHub Support can dereference those pull requests and run garbage
collection, and it only does so for sensitive data, such as credentials that
can't be rotated. The CSVs are public open data, so expect Support to
decline. This is acceptable: the data was never secret, and the old commits
don't affect clone size.

## Verify

Confirm the result from a new clone, not from any clone you used above.

```bash
cd /tmp
git clone https://github.com/im-kenough/DineSafeViz.git dsv-verify
cd dsv-verify
git count-objects -vH | grep size-pack
git log --all --oneline -- '*.csv' '*/.terraform/*' '*.tfstate' | head
```

The pack is under 4 MiB, against about 34 MiB for the backup, and `git log` prints
nothing. After both VMs deploy from their new clones, delete
`dsv-backup.git` and `dsv-purge.git`.

## Next steps

- If anything goes wrong, restore with `git push --force --mirror` from
  `dsv-backup.git`.
- For the background, see GitHub's
  [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
  and the
  [git filter-repo documentation](https://github.com/newren/git-filter-repo).
