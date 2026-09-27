# 3. Merge the work

When the bead closes, the worker switches the rig back to `main`, and the bead carries structured results in its metadata:

```text
gc.work_branch: sc-omn/hello-world
gc.work_commit: 1ceb413...
gc.work_outcome: shipped
gc.work_verification: bats hello.bats; shellcheck hello.sh hello.bats; ...
```

Those fields are what a formula or an order can read later, which is handy for the epic-loop port. Merging is still yours to do, since there's no remote and so no PR:

```bash
cd ~/scratch
git log --oneline --all -5
git merge sc-omn/hello-world
```

`gc rig add` also leaves files uncommitted in the rig: `.gitignore`, `.beads/metadata.json`, `.beads/identity.toml` and `.gc/`. Read `git diff .gitignore` before committing any of them. `.gc/` is runtime state and belongs in `.gitignore`, not in the repo's history.

