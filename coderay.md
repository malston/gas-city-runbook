# Running coderay on Gas City

Sep 22, 2026 · @Someone

coderay can run on the city you already built for scratch, and every command and config key here was checked against the Gas City 1.4.2 source. It assumes the scratch runbook is done: `~/city` exists, the `gc` alias is gone, Dolt has an author, and `~/.claude-gc-worker` is set up.

## Before you start

coderay carries more risk than scratch did, for four reasons.

|  | scratch | coderay |
| --- | --- | --- |
| Beads | New store made by `gc rig add` | Existing store, adopted with `--adopt` |
| Remote | None | GitHub, so workers can push and open PRs |
| Checkout | The worker used it directly | The worker must use its own worktree |
| Commit author | Anything worked | Shows up on GitHub |

Work through this list before touching the city.

1. Make sure no `/epic-loop` run is in progress in coderay. Never let `/epic-loop` and a Gas City worker work the same epic at the same time.
2. Leave the main checkout clean and on `main`. Check with `git -C ~/code/coderay status`.
3. Record the bead prefix and how bd stores its data. `gc rig add --adopt` has to match the prefix exactly.

   ```bash
   grep -i prefix ~/code/coderay/.beads/config.yaml
   cd ~/code/coderay && bd context
   ```
4. Record a baseline you can check against later. Pick an epic you know well and save its current state.

   ```bash
   cd ~/code/coderay
   bd show <epic-id> > ~/coderay-baseline.txt
   bd ready >> ~/coderay-baseline.txt
   ```
5. Back up the beads directory.

   ```bash
   tar czf ~/coderay-beads-$(date +%F).tgz -C ~/code/coderay .beads
   ```

   If `bd context` shows the data living outside `.beads` (a Dolt server somewhere else), back that up too. The tarball only covers the directory.

## Add coderay as a suspended rig

Add the rig with `--adopt`, so Gas City keeps coderay's existing store, and `--start-suspended`, so no worker starts before the rest of this doc is done.

```bash
cd ~/city
gc rig add ~/code/coderay --adopt --start-suspended
gc import install
```

Three things to know about that command:

- Without `--adopt`, `gc rig add` refuses, because `.beads` already holds a store. `--adopt` needs `.beads/metadata.json` and an `issue_prefix` in `.beads/config.yaml`.
- Leave out `--prefix`. The rig takes the prefix from the existing store, and a different one is rejected.
- A suspended rig keeps its beads readable, but the controller skips its agents and `gc hook` hands out no work.

Then check that the beads you recorded are all there.

```bash
gc rig list
gc bd --rig coderay show <epic-id>
cd ~/code/coderay && bd show <epic-id>
cd ~/city && gc doctor | grep -E 'coderay|dolt|✗'
```

Compare both `show` outputs with `~/coderay-baseline.txt`. In `gc doctor`, look at `dolt-drift` and the `rig:coderay:*` lines. `gc rig list` also shows the default branch Gas City picked up from `origin/HEAD`.

This check matters because an adopted rig uses the city's Dolt server by default. I couldn't confirm from the source how an existing store's data reaches that server when bd was running its own. If the epic is missing or `doctor` reports drift, stop there. Don't create beads through `gc`, since that would split the data between two stores. Run `gc rig remove coderay`, which only removes the rig's entries from `city.toml` and `.gc/site.toml`. Then restore the tarball if anything in `.beads` changed, and look into it before trying again.

If everything matches, finish the rig setup:

- Register a Dolt backup for the rig. This is real data now. `gc doctor` prints the exact command in the `rig:coderay:dolt-backup` hint, and it needs the port from `gc dolt status`.
- Review what `gc rig add` wrote into the repo with `git -C ~/code/coderay status`. On scratch it changed `.gitignore` and added files under `.beads` and `.gc/`. `.gc/` is runtime state and belongs in `.gitignore`. Commit the `.gitignore` change through a branch and PR, like any other change to coderay.

## Configure the coderay worker

One city-level patch gives `coderay/claude` its own model, identity, Claude config and worktree, and limits it to one session at a time. Add it to the end of `~/city/city.toml`:

```toml
[[patches.agent]]
dir = "coderay"
name = "claude"
option_defaults = { effort = "medium", model = "sonnet" }
max_active_sessions = 1
work_dir = ".gc/worktrees/coderay/{{.AgentBase}}"
pre_start = [
  "git -C {{.RigRoot}} fetch origin",
  "test -e {{.WorkDir}}/.git || git -C {{.RigRoot}} worktree add --detach {{.WorkDir}} origin/main",
]
env_remove = ["ANTHROPIC_API_KEY"]
env = { CLAUDE_CONFIG_DIR = "/Users/markalston/.claude-gc-worker", GIT_AUTHOR_NAME = "Mark Alston (gc worker)", GIT_COMMITTER_NAME = "Mark Alston (gc worker)", GIT_AUTHOR_EMAIL = "<your GitHub noreply address>", GIT_COMMITTER_EMAIL = "<your GitHub noreply address>" }
```

It has to be `[[patches.agent]]` at city level, for the same reason as on scratch: `claude` is an implicit agent, and a rig-level patch can't reach it. Each line does one job.

| Setting | What it does | Why for coderay |
| --- | --- | --- |
| `option_defaults` | Sets `--model` and `--effort` on the launch command | Sonnet at medium keeps the smoke test cheap. Raise it to `opus` and `high` for real beads. |
| `max_active_sessions = 1` | Caps the pool at one worker | Matches the epic loop, one bead at a time, so two PRs never touch the same files |
| `work_dir` | Runs the session in its own directory under `~/city/.gc/worktrees` | Keeps workers out of `~/code/coderay`, which belongs to you |
| `pre_start` | Fetches, then creates a detached worktree at `origin/main` if one isn't there yet | The worker branches from there, as the epic loop does |
| `env_remove` | Drops `ANTHROPIC_API_KEY` from the session | Same reason your epic-loop driver strips it: it switches Claude to API billing |
| `CLAUDE_CONFIG_DIR` | Points Claude at the worker config | Keeps your personal rules and plugins out of the worker |
| `GIT_*` | Sets the commit author and committer | These commits end up on GitHub |

On identity: GitHub links a commit to an account by its email address. Your noreply address (from GitHub's email settings) links the commits to you, while the "(gc worker)" name keeps them easy to spot in `git log`. A made-up address like `gc-worker@localhost` links to no one.

The worktree is created once per pool slot and reused by later sessions. `{{.AgentBase}}` should name the slot, but I couldn't confirm its exact value for a pool. The `WORKDIR` column of `gc session list` shows the real path once the first session starts. Because the worktree is reused, the worker should start every bead on a fresh branch from `origin/main`. Put that rule in `~/.claude-gc-worker/CLAUDE.md` if coderay's own `CLAUDE.md` doesn't already say it. The repo's `CLAUDE.md` still applies, because Claude reads it from the worktree.

Pushes and PRs run as you. `gh` keeps its login outside the Claude config, so `gh auth status` is the check. If `git -C ~/code/coderay remote -v` shows an SSH remote and the first push fails with an auth error, the session probably has no SSH agent. `gh auth setup-git` with an HTTPS remote avoids that.

Validate right after saving, since a file that won't load also breaks running workers:

```bash
cd ~/city
gc config show --validate
gc config show | grep -n -A14 'dir = "coderay"'
```

## Expect one trust prompt

The first coderay worker will almost certainly die at Claude's folder-trust prompt, and that's expected. Claude records trust per folder in the config directory, and the worker runs in a new folder, the worktree, that `~/.claude-gc-worker` has never seen. The worktree only exists once `pre_start` has run, so you can't answer the prompt ahead of time.

When it happens, the session loops in `start-pending` with a new ID every few seconds, just as on scratch. The loop is harmless: nothing gets claimed until a session is active. Find the folder, answer the prompt once, and the next attempt gets through.

```bash
cd ~/city
gc session list
```

The `WORKDIR` column shows the worktree path. `gc supervisor logs` shows it too, in the `Accessing workspace:` line of the prompt text. Then:

```bash
cd <that worktree path>
CLAUDE_CONFIG_DIR=~/.claude-gc-worker claude --dangerously-skip-permissions
```

Pick *Yes, I trust this folder*, accept anything else it asks, then type `/exit`. Because the worktree is reused, this is a one-time step per pool slot. With `max_active_sessions = 1` there is only one slot.

## Resume the rig and run a smoke test

The first real job should be one small, low-risk bead, such as a typo fix. It proves every setting above before a whole epic depends on them.

Create the bead in coderay's store and note the ID `bd create` prints:

```bash
cd ~/code/coderay
bd create "<small, low-risk task>"
```

In a second terminal, start watching launch commands before anything launches:

```bash
cd ~/city
gc events --follow | grep -o '"command":"claude[^"]*"'
```

Then resume the rig and hand the bead to its worker:

```bash
cd ~/city
gc rig resume coderay
gc sling coderay/claude <bead-id>
```

Answer the trust prompt when the loop starts, as described above. Then check each of these while the worker runs and after the bead closes.

| Check | Command | Expect |
| --- | --- | --- |
| Model and effort | The `gc events` terminal | `--model claude-sonnet-5` and `--effort medium`, not `--effort max` |
| Worker config | `gc session peek <session-id>` | None of your personal status lines at the bottom |
| Worktree | `gc session list` | `WORKDIR` under `~/city/.gc/worktrees/coderay` |
| Your checkout | `git -C ~/code/coderay status` and `git -C ~/code/coderay branch --show-current` | Still clean, still `main` |
| Author | `git -C <worktree> log -1 --format='%an <%ae>'` | The worker name and your noreply address |
| Push and PR | `gh pr list` | Whatever the worker did, under your GitHub account |
| Result | `gc bd --rig coderay show <bead-id>` | Closed, with `gc.work_branch`, `gc.work_commit` and `gc.work_outcome` |

The default formula, `mol-do-work`, never pushed on scratch because there was no remote. I don't know yet whether it pushes and opens a PR once a remote exists, and with your personal rules out of the worker, coderay's own `CLAUDE.md` and the formula now decide. The `Push and PR` check answers that. Merging stays yours either way: review whatever it opened the way you'd review any PR.

## Working an epic

Keep running `/epic-loop` for epics you care about until the loop is ported to a formula. The default `mol-do-work` worker does none of the loop's quality steps on its own. On scratch it wrote tests, ran a mutation check and asked for a review only because it loaded your personal rules, and the worker config above takes those away on purpose.

| Epic-loop step | Default worker with this setup | Where it goes in a port |
| --- | --- | --- |
| Worktree per bead from `origin/main` | One reused worktree per pool slot | `pre_start`, or an isolate step |
| Failing test first, guard mutated both ways | Only if coderay's `CLAUDE.md` asks | A `check` step running a verify script |
| PR labeled `epic-loop`, wait for CI | Not known yet (the smoke test shows it) | An open-PR step |
| Review in a fresh context | None | A separate reviewer agent, or `mol-review-quorum` |
| Fix serious findings, file the rest to a findings epic | None | A fix-or-file step |
| Merge or hold, then close the bead | Closes the bead, leaves the merge to you | Two steps gated on a `hold` variable |
| `human` tag for design questions | None | A rule in the worker's prompt |
| Turn and spend budget | No spend cap found in 1.4.2 | `max_active_sessions`, plus watching usage yourself, since the worker config has no token-ledger plugin |

For small, self-contained beads, Gas City works now. Sling each ready child to the pool, in the order you want it done:

```bash
cd ~/code/coderay && bd ready
cd ~/city && gc sling coderay/claude <child-id>
```

With `max_active_sessions = 1`, slung beads wait for the one worker, so they're worked one at a time. Two cautions apply. The worker won't read the epic's DESIGN field unless something tells it to, so put per-bead instructions in each child's own description. And never sling children of an epic that `/epic-loop` is working at the same time.

The port itself is the formula sketch from earlier in this conversation: an `epic-bead` item formula with the steps in the table, and an outer formula with a `drain` step over the epic's children. Check its keys against the v1.4.2 formula spec before writing it. The docs on `main` run ahead of the release.

## Pausing and rolling back

Suspending the rig is the quick stop. The controller skips its agents and `gc hook` hands out no work, while the beads stay readable.

```bash
cd ~/city
gc rig suspend coderay
gc session list
```

If a coderay session is still listed afterward, end it with `gc session kill <session-id>`. Its bead stays open for the next worker. `gc rig resume coderay` brings the rig back.

To take coderay out of Gas City entirely:

1. `gc rig remove coderay`. This only removes the rig's entries from `city.toml` and `.gc/site.toml`. coderay's `.beads` stays where it is.
2. Delete the `[[patches.agent]]` block for `dir = "coderay"` and run `gc config show --validate`.
3. Remove the worker's worktree. `git -C ~/code/coderay worktree list` shows it, then `git -C ~/code/coderay worktree remove <path>` and `git -C ~/code/coderay worktree prune`.
4. Revert the `.gitignore` change `gc rig add` made, if you'd committed it.

Restore the `.beads` tarball only if the store itself was damaged, and only after nothing, neither Gas City nor `/epic-loop`, is using it.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `gc rig add` refuses because `.beads` already holds a store | `--adopt` was left off | Run it again with `--adopt --start-suspended` |
| `--adopt: rig "coderay" already has bead prefix ...` | A `--prefix` that doesn't match the store | Drop `--prefix` |
| `--adopt requires a valid issue_prefix` | `.beads/config.yaml` has no prefix | Check the store with `bd context` before adopting |
| The epic is missing from `gc bd --rig coderay`, or `gc doctor` reports `dolt-drift` | Gas City and bd are reading different stores | Stop. Create nothing through `gc`, run `gc rig remove coderay`, and look into it |
| Sessions loop in `start-pending` with new IDs | The trust prompt for the worktree | Answer it in the `WORKDIR` path, as in the trust section |
| `gc supervisor logs` shows a `pre_start` failure | A worktree command failed. The log keeps the last 4 KiB of its output | Run the two commands by hand with real paths. If the default branch isn't `main`, change `origin/main` to match |
| A worker changes files in `~/code/coderay` | `work_dir` didn't apply | `gc rig suspend coderay`, then check `WORKDIR` in `gc session list` and the patch in `gc config show` |
| The launch command still has `--effort max` | The session started before the patch, or the patch didn't load | Wait for a new session. If it persists, check `gc config show --validate` |
| The first push fails with an auth error | No SSH agent in the session | Switch the remote to HTTPS and run `gh auth setup-git` |
