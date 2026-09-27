# 2. Watch a worker

The dashboard link from `sling` is the easiest view. It shows each step of the workflow as it moves from pending to running to closed, and the _Session_ tab shows the agent's live session.

From the terminal:

```bash
gc session list
gc session peek <session-id>
gc bd --rig scratch show sc-omn
```

A healthy worker keeps the same ID with a growing `AGE`. `peek` shows its screen without attaching. `gc bd --rig` reads the rig's store from anywhere, and plain `bd show` from inside `~/scratch` works too. Plain `bd show` from `~/city` looks in the city's store and reports `no issue found`.

The bead stays `OPEN` the whole time the worker has it. Gas City records the claim in metadata, and `gc.last_heartbeat_at` shows the worker checking in.

To attach instead of peeking, run `gc session attach <session-id>` and detach with `Ctrl-b d` so the session keeps running.

While a worker is active, stay out of the rig's Git checkout. The default worker has no worktree. It creates a branch named after the bead and checks it out right in `~/scratch`, so switching branches or committing there pulls the branch out from under it. Your shell prompt's own `git status` is harmless, but the worker notices it and says another command ran in the repository.

Don't run the commands you see in `peek` yourself. `gc hook --claim --drain-ack --json` is the worker asking the city for work. In your shell it fails with `agent not specified`, and if you pass it an agent name it will claim beads meant for the worker.


## What to expect on the dashboard

A few things on the first run look odd but are normal.

The run header shows `V1`. `mol-do-work` uses the older formula compiler. Formulas you write should declare `formula_compiler = ">=2.0.0"` to get `check`, `retry` and `drain`.

The _Diff_ tab says no diff is available because the run recorded no `work_dir`. That's the missing worktree described above. A port of the epic loop needs to set up per-bead worktrees itself. In 1.4.2 there's no `gc worktree` command for that. It's config and script wiring: an agent's `work_dir` plus a `pre_start` script that runs `git worktree add`.

_Health_ may show a badge, and `gc supervisor logs` may show `slow_storage_degraded` traces. Those point at Dolt. A brief `dolt circuit breaker is open` error is also possible. It happened once on the first install and cleared by itself within a minute, since the breaker retries every 5 seconds. `gc beads health` checks the store and tries to recover it, and `gc doctor` covers the rest.

`gc doctor` on a fresh city shows three warnings that need no action for a scratch rig. `formula-requirements` is about bundled pack formulas, not yours. `jsonl-archive` means the event archive has no off-box copy. `rig:<name>:dolt-backup` means the rig's beads have no backup registered, and its hint has the command to fix that for a rig you care about.

