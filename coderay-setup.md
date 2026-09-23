# Adding coderay to Gas City

This adds coderay as a rig in an existing city, so Gas City workers can take coderay tasks. It assumes [gas-city-setup.md](gas-city-setup.md) steps 1 to 4 are done: Gas City is installed, the `gc` alias is gone, Dolt has an identity, and `~/city` is running. Steps marked _verified_ were run on Gas City 1.4.2 and bd 1.3.0, and the output shown is what they printed.

## Why a separate clone

The rig is a second clone at `~/gc-rigs/coderay`. `~/code/coderay` stays exactly as it is.

coderay already has its own beads store: embedded Dolt, prefix `coderay`, with `.beads/config.yaml` and `.beads/metadata.json` tracked in Git. Gas City 1.4.2 can't take that store over as it is:

- `gc rig add` refuses any directory whose `.beads/` holds either of those files.
- `gc rig add --adopt` needs an `issue_prefix` in `config.yaml`, which coderay's doesn't set. Even with one, adopting switches the store to `dolt_mode: server` on the city's Dolt server. The city's database starts out empty and the existing beads aren't copied into it. After that, your own `bd` in coderay only works while the city's Dolt server is up, and gc turns off bd's backups.

So there are two separate backlogs:

| Where               | Prefix     | Who uses it                                                    |
| ------------------- | ---------- | -------------------------------------------------------------- |
| `~/code/coderay`    | `coderay-` | You, with plain `bd`, as today                                 |
| `~/gc-rigs/coderay` | `cr-`      | Gas City workers, through `gc sling` and `gc bd --rig coderay` |

Workers can't see `coderay-` beads. To hand one over, sling its text or create a `cr-` bead that names it.

## 1. Clone coderay (verified)

Clone from GitHub, not from `~/code/coderay`. A local clone's `origin` would point at your working copy, and branches pushed there never reach GitHub.

```bash
mkdir -p ~/gc-rigs
git clone https://github.com/malston/coderay.git ~/gc-rigs/coderay
```

## 2. Remove the clone's beads store files (verified)

Without this, `gc rig add` stops with:

```text
gc rig add: /Users/markalston/gc-rigs/coderay/.beads already contains a beads store; use --adopt to register it, or remove /Users/markalston/gc-rigs/coderay/.beads to reinitialize
```

It checks nothing else, and `city.toml` is untouched when it refuses. Removing only the two store files is enough. gc treats a `.beads/` without them as "not a store" and builds a new one in place, so the tracked hooks and README stay put.

```bash
cd ~/gc-rigs/coderay
rm .beads/metadata.json .beads/config.yaml
```

## 3. Add the rig (verified)

```bash
cd ~/city
gc rig add ~/gc-rigs/coderay --prefix cr
```

Expected output:

```text
Adding rig 'coderay'...
  Detected git repo at /Users/markalston/gc-rigs/coderay
  Prefix: cr
  Default branch: main
  Import: gc=https://github.com/gastownhall/gascity-packs/tree/main/gascity/roles (default)
  Initialized beads database
  Generated routes.jsonl for cross-rig routing
Rig added.
```

`--prefix cr` keeps worker bead IDs apart from your `coderay-` ones. Without it, gc derives a prefix from the rig name.

## 4. Undo the commit `bd init` made (verified)

`gc rig add` runs `bd init`, and `bd init` commits on the clone's `main` under your own Git identity. The commit is `bd init: initialize beads issue tracking`. It rewrites `.beads/config.yaml` and `.beads/metadata.json` for the city's Dolt server, including this machine's host and port, and edits both `.gitignore` files. gc then appends more lines to `.gitignore` without committing them.

Leave it and every branch a worker makes starts from that commit, so every PR carries it. Drop the commit but keep its files, since the rig needs them:

```bash
cd ~/gc-rigs/coderay
git log --oneline -2
git reset --soft origin/main
git reset
```

`git log` should show the `bd init` commit on top before the reset. After it, the files are back to plain local changes.

Tell Git to ignore local changes to them, so no worker can commit them:

```bash
git update-index --skip-worktree .beads/.gitignore .beads/config.yaml .beads/metadata.json .gitignore
```

Two untracked files are left to hide. gc's `.gitignore` lines end with `!.beads/identity.toml`, which un-ignores that file, and a pattern in a `.gitignore` beats `.git/info/exclude`. A rule in `.beads/.gitignore` does win, because the deeper file takes precedence, and Git now ignores edits to that file too:

```bash
printf '%s\n' 'identity.toml' >> .beads/.gitignore
printf '%s\n' '.gc/' >> .git/info/exclude
git status -sb
```

`git status -sb` should print only `## main...origin/main`. `git ls-files -v` marks the four files with `S`.

gc writes the top-level `.gitignore` only during `rig add` and `init`, and never writes `.beads/.gitignore`, so a city restart doesn't undo this. It does rewrite `metadata.json` and `config.yaml` on start, which `--skip-worktree` hides.

The cost of `--skip-worktree` is on pulls. If a commit on GitHub changes one of those four files, `git pull` in the clone refuses to overwrite it. Then run `git update-index --no-skip-worktree <file>`, move your copy aside, pull, put the gc lines back, and mark it again.

## 5. Install the rig's packs (verified)

```bash
cd ~/city
gc import install
gc agent list | grep coderay
```

`gc import install` prints `Installed 4 remote import(s)`. The agent list should include `coderay/claude`, `coderay/codex`, `coderay/gemini` and the `coderay/gc.*` roles, all `active`.

## 6. Set up the clone's Python environment (verified)

Workers run coderay's tests the way coderay's `CLAUDE.md` says to. Give them a working environment and check it's green before any worker touches the repo:

```bash
cd ~/gc-rigs/coderay
make install
make test
```

The baseline was `1919 passed, 1 skipped in 40.22s`. If a worker later reports failures, compare against this.

The clone has no `.env`, since it's gitignored. The tests don't need an API key. Don't copy `~/code/coderay/.env` into the clone unless you want workers running live `crawl` commands, which bill that key.

## 7. Tune the worker (verified)

Add a patch to the end of `~/city/city.toml`, the same shape as runbook step 7 with `dir = "coderay"`:

```toml
[[patches.agent]]
dir = "coderay"
name = "claude"
option_defaults = { effort = "medium", model = "sonnet" }
env = { GIT_AUTHOR_NAME = "Gas City worker", GIT_AUTHOR_EMAIL = "gc-worker@localhost", GIT_COMMITTER_NAME = "Gas City worker", GIT_COMMITTER_EMAIL = "gc-worker@localhost" }
```

Validate and check it landed:

```bash
cd ~/city
gc config show --validate
gc doctor | grep -E '✗|coderay'
gc config show | awk '/^\[\[agent\]\]/ { if (b ~ /name = "claude"\ndir = "coderay"/) printf "%s", b; b = "" } { b = b $0 "\n" }'
```

`gc config show --validate` ends with `Config valid.` It also prints two warnings about `core.control-dispatcher` and `max_active_sessions=1`, which come from the bundled pack and need no action. `gc doctor` should show every `rig:coderay` check passing except `rig:coderay:dolt-backup`, a warning that the `cr` store has no backup registered. The merged `claude` agent for `coderay` should show the `[agent.env]` lines and `effort = "medium"`, `model = "sonnet"`.

## 8. Give workers their own Claude config and trust the clone (not yet run)

Follow "Give workers their own Claude config" in runbook step 7, running the one-time `claude` command in this rig:

```bash
mkdir -p ~/.claude-gc-worker
cd ~/gc-rigs/coderay
CLAUDE_CONFIG_DIR=~/.claude-gc-worker claude --dangerously-skip-permissions
```

Answer every prompt, including _Yes, I trust this folder_, then `/exit`. Then add `CLAUDE_CONFIG_DIR = "/Users/markalston/.claude-gc-worker"` to the coderay patch's `env`, and add `observe_paths` under `[daemon]`, as the runbook shows. Validate again.

If you skip the separate config for now, still trust the folder with plain `claude` in `~/gc-rigs/coderay`. Otherwise the first worker loops on the trust prompt.

coderay's own `CLAUDE.md` and `.claude/settings.json` come with the clone, so workers get the project's rules either way. The settings run `bd prime --hook-json` at session start. `bd` in the clone reads the clone's `cr` store, not your `coderay-` beads: `bd list` there printed `No issues found.` right after step 3.

## 9. Route a first job (not yet run)

Pick something small and self-contained, then sling it from `~/city` with your own description in the quotes:

```bash
cd ~/city
gc sling coderay/claude "Describe one small coderay task here"
```

Expect a `cr-` bead and a `mol-do-work` workflow, then watch it as in runbook step 9, with `gc bd --rig coderay show <cr-id>`. Stay out of the clone's checkout while a worker has it. The worker switches branches right there.

Don't sling `mol-polecat-commit` at this rig. It works in a worktree off `origin/main`, then runs `git push origin HEAD:main`, which pushes straight to `main` with no PR.

## 10. Get the work to GitHub

When the bead closes, the branch is in the clone and nothing has been pushed. Review it, then push and open the PR yourself:

```bash
cd ~/gc-rigs/coderay
git log --oneline main..<branch>
make test
git push -u origin <branch>
gh pr create --head <branch>
```

The four `--skip-worktree` files never go with it. Commits show `Gas City worker` as the author.

Don't run `bd sync` or `bd dolt push` in the clone. `bd init` set `sync.remote` in `.beads/config.yaml` to `git+https://github.com/malston/coderay.git`, and `bd sync` pushes to that Dolt remote. The `cr` store would land on GitHub next to the code. GitHub had no `refs/dolt/*` refs when this was written (`git ls-remote origin 'refs/dolt/*'` printed nothing).

## Removing the rig

```bash
cd ~/city
gc rig remove coderay
```

This removes the `[[rigs]]` entry and the rig's path binding. It doesn't remove the `[[patches.agent]]` block for `coderay`, so delete that by hand. Then `rm -rf ~/gc-rigs/coderay`. `~/code/coderay` was never touched.

## Troubleshooting

| Symptom                                                                      | Cause                                                                | Fix                                                 |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------- |
| `.beads already contains a beads store; use --adopt ...`                     | The clone still has `metadata.json` or `config.yaml` in `.beads/`    | Step 2                                              |
| `--adopt requires a valid issue_prefix in .beads/config.yaml`                | Tried `--adopt` on coderay's committed store                         | Don't adopt. Use steps 2 and 3                      |
| Clone shows `[ahead 1]` after `rig add`                                      | `bd init` committed on `main`                                        | Step 4                                              |
| `git status` shows `.beads/identity.toml`                                    | The `!.beads/identity.toml` line in `.gitignore` un-ignores it       | Add `identity.toml` to `.beads/.gitignore` (step 4) |
| `git pull` in the clone refuses to overwrite `.gitignore` or a `.beads` file | Upstream changed a `--skip-worktree` file                            | See the end of step 4                               |
| `bd show coderay-xxx` fails in the clone                                     | The clone's store is `cr`. `coderay-` beads live in `~/code/coderay` | Run it in `~/code/coderay`                          |
| Worker loops in `start-pending`                                              | Trust or first-run prompt unanswered for this folder                 | Step 8, and the runbook's troubleshooting table     |
