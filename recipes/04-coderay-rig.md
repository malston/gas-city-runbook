# Adding coderay to Gas City

This adds coderay as a rig in an existing city, so Gas City workers can take coderay tasks. It assumes [SETUP.md](../SETUP.md) steps 1 to 4 are done: Gas City is installed, the `gc` alias is gone, Dolt has an identity, and `~/city` is running. Steps marked _verified_ were run on Gas City 1.4.2 and bd 1.3.0, and the output shown is what they printed.

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

gc's own code writes the top-level `.gitignore` only during `rig add` and `init` (`cmd/gc/cmd_rig.go`, `cmd/gc/cmd_init.go`), and it doesn't write `.beads/.gitignore`. bd does append to `.beads/.gitignore` (its "Added by bd (missing required patterns)" block), but an append leaves the `identity.toml` line in place. gc does write `metadata.json` and `config.yaml` itself when it sets up the store, and `--skip-worktree` hides any later rewrite of those too.

The cost of `--skip-worktree` is on pulls. If a commit on GitHub changes one of those four files, `git pull` in the clone refuses to overwrite it. Then run `git update-index --no-skip-worktree <file>`, move your copy aside, pull, put the gc lines back, and mark it again.

### Remove the store's Dolt remote (verified)

`bd init` also gives the `cr` store a Dolt remote named `origin`, pointing at `git+https://github.com/malston/coderay.git`, and writes the same URL to `sync.remote` in `.beads/config.yaml`. Leave them and bd pushes the store to GitHub on its own. On the first job, about a minute after `gc sling`, GitHub gained `refs/dolt/data` and a `__dolt_remote_info__` branch holding the six `cr-` beads, pushed under your Git identity, with no push command in the worker's transcript. bd's help mentions the feature only as "`--sandbox`: disables Dolt auto-push".

Remove both:

```bash
cd ~/gc-rigs/coderay
bd dolt remote remove origin
perl -0pi -e 's/\nsync:\n\s+remote: "[^"]*"\n?/\n/' .beads/config.yaml
bd dolt remote list
bd config get sync.remote
```

Expect `No remotes configured.` and `sync.remote (not set in config.yaml)`. `bd config unset sync.remote` isn't enough: it reports success, but `bd init` wrote the value as a nested `sync:` block, and that block stays.

If a push already happened, delete it from GitHub:

```bash
git ls-remote origin 'refs/dolt/*' 'refs/heads/__dolt_remote_info__'
git push origin --delete refs/dolt/data refs/heads/__dolt_remote_info__
```

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

Add a patch to the end of `~/city/city.toml`, the same shape as [SETUP.md](../SETUP.md) step 7 with `dir = "coderay"`:

```toml
[[patches.agent]]
dir = "coderay"
name = "claude"
option_defaults = { effort = "medium", model = "sonnet" }
max_active_sessions = 1
env = { GIT_AUTHOR_NAME = "Gas City worker", GIT_AUTHOR_EMAIL = "gc-worker@localhost", GIT_COMMITTER_NAME = "Gas City worker", GIT_COMMITTER_EMAIL = "gc-worker@localhost" }
```

`max_active_sessions = 1` caps the rig at one Claude worker. Every worker here shares the one checkout (step 9 explains why), so two at once would commit over each other.

`gc-worker@localhost` links the commits to no GitHub account once they're in a PR. If you want them linked to you, use your GitHub noreply address as the email and keep the worker name so they stay easy to spot.

Validate and check it landed:

```bash
cd ~/city
gc config show --validate
gc doctor | grep -E '✗|coderay'
gc config show | awk '/^\[\[agent\]\]/ { if (b ~ /name = "claude"\ndir = "coderay"/) printf "%s", b; b = "" } { b = b $0 "\n" }'
```

`gc config show --validate` ends with `Config valid.` It also prints two warnings about `core.control-dispatcher` and `max_active_sessions=1`, which come from the bundled pack and need no action. `gc doctor` should show every `rig:coderay` check passing except `rig:coderay:dolt-backup`, a warning that the `cr` store has no backup registered. The merged `claude` agent for `coderay` should show `max_active_sessions = 1`, the `[agent.env]` lines and `effort = "medium"`, `model = "sonnet"`.

Check that workers won't bill your API key. Sessions start from the supervisor's environment, and gc answers Claude's "use this API key?" prompt with Yes on its own (`internal/runtime/dialog.go`). So if `ANTHROPIC_API_KEY` reaches the supervisor, workers run on API billing, not your plan. `env_remove` in a patch doesn't help here. It only removes keys from the agent's own `env` table (`internal/config/patch.go`).

```bash
ps eww -p "$(pgrep -f 'gc supervisor' | head -1)" | grep -q 'ANTHROPIC_API_KEY=' && echo "supervisor HAS the key" || echo "supervisor: no key"
```

When this was written it printed `supervisor: no key`, even though `launchctl getenv ANTHROPIC_API_KEY` was set. If it ever prints `HAS the key`, find where the supervisor picks it up before you sling work.

## 8. Give workers their own Claude config and trust the clone (verified)

Follow "Give workers their own Claude config" in [SETUP.md](../SETUP.md) step 7, running the one-time `claude` command in this rig:

```bash
mkdir -p ~/.claude-gc-worker
cd ~/gc-rigs/coderay
CLAUDE_CONFIG_DIR=~/.claude-gc-worker claude --dangerously-skip-permissions
```

Answer every prompt, including _Yes, I trust this folder_, then `/exit`. Check that the answers were saved:

```bash
python3 -c "
import json; d = json.load(open('$HOME/.claude-gc-worker/.claude.json'))
print('trusted:', d['projects']['$HOME/gc-rigs/coderay'].get('hasTrustDialogAccepted'))
print('logged in:', bool(d.get('oauthAccount')))"
cat ~/.claude-gc-worker/settings.json
```

Expect `trusted: True`, `logged in: True`, and `"skipDangerousModePermissionPrompt": true` in `settings.json`.

Then add `CLAUDE_CONFIG_DIR` to the front of the coderay patch's `env`:

```toml
env = { CLAUDE_CONFIG_DIR = "/Users/markalston/.claude-gc-worker", GIT_AUTHOR_NAME = "Gas City worker", GIT_AUTHOR_EMAIL = "gc-worker@localhost", GIT_COMMITTER_NAME = "Gas City worker", GIT_COMMITTER_EMAIL = "gc-worker@localhost" }
```

If `city.toml` has no `[daemon]` table yet, add one near the top, after `[workspace]`:

```toml
[daemon]
observe_paths = ["/Users/markalston/.claude-gc-worker/projects"]
```

Validate again with `gc config show --validate`, and rerun the `awk` check from step 7. It should now also show `CLAUDE_CONFIG_DIR`.

If you skip the separate config for now, still trust the folder with plain `claude` in `~/gc-rigs/coderay`. Otherwise the first worker loops on the trust prompt.

coderay's own `CLAUDE.md` and `.claude/settings.json` come with the clone, so workers get the project's rules either way. The settings run `bd prime --hook-json` at session start. `bd` in the clone reads the clone's `cr` store, not your `coderay-` beads: `bd list` there printed `No issues found.` right after step 3.

### Keep workers out of your shared Python (verified)

coderay's `CLAUDE.md` gives `pip install -e .` as the raw install command. On the first job the worker ran exactly that in the clone. Plain `pip` on its `PATH` was the shared mise Python 3.14.2, not the clone's `.venv`. That interpreter already had an editable `crawl` pointing at `~/code/coderay`, and the worker's install switched it to `~/gc-rigs/coderay`. A Claude session in `~/code/coderay` running plain `pytest` then tested the clone's code. Only `make` and `uv run` use the clone's `.venv`.

Give workers a rule of their own in `~/.claude-gc-worker/CLAUDE.md`:

```markdown
# Gas City worker rules

You share this machine's Python with other sessions. Never install packages into it.

- Never run `pip`, `pip3`, `pip install` or `python -m pip`. Plain `python` and `pip` here are a shared interpreter, and an install changes it for every other session.
- In a repo with a `Makefile`, run tests with `make test`. Otherwise use `uv run pytest`. Both use the repo's own `.venv`.
- If the repo's `.venv` is missing or out of date, run `make install` (or `uv sync --locked`). Never install anything outside the repo.
- If a repo's own docs tell you to run `pip install -e .`, use `make install` instead.
```

Check that the worker config loads it (one Haiku call):

```bash
cd ~/gc-rigs/coderay
CLAUDE_CONFIG_DIR=~/.claude-gc-worker claude -p --model haiku "Without running any tools: what does your user-level instructions file say about pip? Quote its first bullet exactly."
```

It should quote the first bullet. This is an instruction, not a lock, so a worker can still ignore it. To see whether it did, check which checkout the shared install points at:

```bash
~/.local/share/mise/installs/python/3.14.2/bin/pip show crawl | grep 'Editable project location'
```

It should say `/Users/markalston/code/coderay`. If it says `gc-rigs`, run `pip install -e .` from `~/code/coderay` with that same `pip`.

## 9. Route a first job (not yet run)

Pick something small and self-contained, then sling it from `~/city` with your own description in the quotes:

```bash
cd ~/city
gc sling coderay/claude "Describe one small coderay task here"
```

Expect a `cr-` bead and a `mol-do-work` workflow, then watch it as in [recipe 2](02-watch-a-worker.md), with `gc bd --rig coderay show <cr-id>`. Stay out of the clone's checkout while a worker has it.

The sling text becomes the bead's title only. Its description is `(none)`, and the worker can't read your `coderay-` beads. To hand over one of those beads in full, copy its description into the new `cr-` bead right after the sling:

```bash
cd ~/code/coderay
bd show coderay-xxx --json | python3 -c "import json,sys; d=json.load(sys.stdin); d=d[0] if isinstance(d,list) else d; print(d['description'])" > /tmp/desc.txt
cd ~/city
gc bd --rig coderay update cr-yyy --body-file /tmp/desc.txt
```

Do it quickly. The worker reads the bead soon after its session starts. On the first job, the session started within seconds of the update.

`gc events` lists the launch command once per `bead.updated` event on the worker's session bead, so the watcher prints the same line several times for one worker. `gc session list` shows whether it's really one session.

Claude Code may show a "Try the new fullscreen renderer?" prompt inside the worker. On the first job it sat there for the whole run, and the worker kept calling tools underneath it.

`mol-do-work` is the default formula, and its own description says "No git branching, no worktree isolation." The worker does the work "in the current working directory," commits, and closes the bead. It has no push step. In this clone that means the commit lands on `main`. On scratch the worker made a branch only because your personal rules told it to.

Don't sling `mol-polecat-commit` at this rig either. It works in a worktree off `origin/main`, then runs `git push origin HEAD:main`, which pushes straight to `main` with no PR.

## 10. Get the work to GitHub (branch move verified)

When the bead closes, the worker's commit sits on the clone's `main`, ahead of `origin/main`, and nothing has been pushed. Move it to a branch, put `main` back, then push and open the PR yourself:

```bash
cd ~/gc-rigs/coderay
git status -sb
git log --oneline origin/main..main
git branch cr-xxx
git reset --keep origin/main
git switch cr-xxx
make test
git push -u origin cr-xxx
gh pr create
git switch main
```

Use the bead ID as the branch name. `git status -sb` should show `[ahead 1]` (or more) before the move and `## main...origin/main` after the reset. This was checked with a throwaway commit: `--keep` put `main` back without touching the four `--skip-worktree` files or the `cr` config.

Those four files never go into the PR. Commits show `Gas City worker` as the author.

Do this before slinging the next bead. The next worker starts from whatever `main` is in the clone.

If GitHub shows a `__dolt_remote_info__` branch with a "Compare & pull request" banner, the store's Dolt remote is back. Redo "Remove the store's Dolt remote" in step 4.

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
| Clone shows `[ahead 1]` after a bead closes                                  | `mol-do-work` commits on the checked-out branch                      | Step 10                                             |
| `git status` shows `.beads/identity.toml`                                    | The `!.beads/identity.toml` line in `.gitignore` un-ignores it       | Add `identity.toml` to `.beads/.gitignore` (step 4) |
| `git pull` in the clone refuses to overwrite `.gitignore` or a `.beads` file | Upstream changed a `--skip-worktree` file                            | See the end of step 4                               |
| `bd show coderay-xxx` fails in the clone                                     | The clone's store is `cr`. `coderay-` beads live in `~/code/coderay` | Run it in `~/code/coderay`                          |
| Worker loops in `start-pending`                                              | Trust or first-run prompt unanswered for this folder                 | Step 8, and the runbook's troubleshooting table     |
