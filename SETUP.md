# Setting up Gas City on a new Mac

This runbook takes a fresh macOS machine to a running Gas City with one rig whose Claude Code worker is ready for a first job. It's written from a first install of Gas City 1.4.2 and folds in every problem that install hit, so you can run it top to bottom without detours.

Each step says what to expect. If the output differs, check [Troubleshooting](#troubleshooting) before moving on.

## Before you start

Run commands one line at a time, at least until step 2 is done. Zsh expands aliases when it reads a pasted block, before any line in that block runs. A multi-line paste that contains `unalias gc` followed by `gc version` will still run the old alias on the second line.

You'll also need Claude Code installed and signed in, since that's the agent this city uses.

The docs in the `gastownhall/gascity` repo track the `main` branch, which runs ahead of the Homebrew release. On the first install, `gc doctor --check` was in the docs but not in 1.4.2. When a flag from the docs fails, `gc <command> --help` shows what your installed version accepts.

## 1. Install Gas City

```bash
brew install gascity
```

Homebrew pulls in all the runtime dependencies (tmux, jq, git, Dolt, flock and the `bd` beads CLI), so there's nothing else to install by hand.

## 2. Remove the Oh My Zsh `gc` alias

Oh My Zsh's `git` plugin defines `gc` as `git commit --verbose`. Until you remove it, every `gc` command runs Git instead, and the failures look like `error: pathspec 'sling' did not match any file(s) known to git`.

Find where your custom Oh My Zsh files live:

```bash
echo "$ZSH_CUSTOM"
```

On your machines this is `~/my-dotfiles/oh-my-zsh`. Oh My Zsh loads every `*.zsh` file there after its plugins, which is the right moment to drop the alias:

```bash
printf '%s\n' 'unalias gc 2>/dev/null' > "$ZSH_CUSTOM/gascity.zsh"
```

If this file is already committed in your dotfiles repo, you can skip the `printf` and just pull.

Open a new terminal tab, then check it:

```bash
type gc
gc version
ls -l "$(command -v gc)"
```

`type gc` should print `/opt/homebrew/bin/gc`, and the symlink should point into `Cellar/gascity/<version>`. Graphviz also ships a `gc` command, so the symlink check catches that case too.

If `$ZSH_CUSTOM` is empty, append the line to the bottom of `~/.zshrc` instead. It has to come after `source "$ZSH/oh-my-zsh.sh"` or the plugin recreates the alias.

To get past the alias for a single command without changing any files, run `command gc version`. The [installation guide](https://docs.gascity.com/getting-started/installation) lists this too.

## 3. Set your Dolt identity

Gas City stores beads in Dolt, and Dolt refuses to initialize without an author. Without this step, `gc init` creates the city and then stops with "startup is blocked by Dolt author identity".

```bash
dolt config --global --add user.name "Mark Alston"
dolt config --global --add user.email "mark.alston@forgd.ai"
dolt config --global --list
```

Every bead change gets recorded under this identity. On the first install it picked up a personal Gmail address from the Git config, so set it explicitly on a machine you use for client work.

## 4. Create and start the city

```bash
gc init ~/city
```

The wizard asks two questions. Choose template `1` (`gascity`), which the tutorials assume and which ships the built-in formulas and the `mayor` agent. Choose agent `1` (Claude Code).

It also prints a usage-metrics notice. It says it sends the command name, the `gc` version, your OS and an anonymous install ID. Run `gc metrics off` if you'd rather not.

If step 3 was done, `init` starts the city on its own. If it stopped on the Dolt identity, fix that and run:

```bash
cd ~/city
gc start
```

You should see `City started under supervisor.` Starting also installs a launchd agent at `~/Library/LaunchAgents/com.gascity.supervisor.plist`, so the city comes back every time you log in.

## 5. Add a rig

A rig is a Git repo the city works in. Most `gc` commands find the city by walking up from your current directory, so run them from `~/city`. A rig directory outside the city (like `~/scratch`) won't work, and you'll get `not in a city directory (no city.toml or .gc/ found)`.

```bash
mkdir -p ~/scratch && git -C ~/scratch init
cd ~/city
gc rig add ~/scratch
```

Expect `Prefix: sc`, `Initialized beads database` and `Rig added.` Bead IDs in this rig will start with `sc-`.

Adding the rig brings in a remote pack of roles from `gastownhall/gascity-packs`, which isn't downloaded yet. Install it before anything else touches the rig:

```bash
gc import install
```

This fetches the packs and writes `packs.lock`, which pins the versions. Skip it and the next command fails with `remote import ... is not installed (missing packs.lock)`.

Last, tell Claude Code to trust the rig folder. Claude asks "Is this a project you created or one you trust?" the first time it opens any directory, and a Gas City session has nobody to answer it. The pane dies with status 1, the pool replaces the session, and it dies the same way every few seconds. On the first install the `mayor` started fine in `~/city` without this, but if it ever loops the same way, the fix is the same.

```bash
cd ~/scratch
claude
```

Pick _Yes, I trust this folder_, then exit with `/exit`. Do this once for every new rig, before you sling work to it. `--dangerously-skip-permissions` doesn't cover this prompt, since it only skips tool permissions.

## 6. Check the agents

```bash
cd ~/city
gc agent list
```

You should see city agents (`mayor`, `claude`, `codex`, `gemini` and some housekeeping ones) and a set of rig agents qualified by the rig name, such as `scratch/claude` and `scratch/gc.implementation-worker`. The `scratch/gc.*` agents are the roles from the pack you just installed.

`claude`, `codex` and `gemini` are implicit agents. Gas City creates one per configured provider, once for the city and once per rig. They don't come from any pack, which matters in the next step.

## 7. Tune the rig's worker before the first job

Left alone, `scratch/claude` launches as `claude --dangerously-skip-permissions --effort max`. That's Opus at maximum effort, carrying your personal Claude Code setup. It loads your `~/.claude` skills, plugins, status lines, `CLAUDE.md` rules and your Git identity. On the first install, a hello world job took about 20 minutes and cost $4.76. It ran bats tests, shellcheck, a mutation check and a code review, because your personal rules told it to. It also committed as you and refused to merge to `main`, again because your rules say so.

Add a patch to the end of `~/city/city.toml`:

```toml
[[patches.agent]]
dir = "scratch"
name = "claude"
option_defaults = { effort = "medium", model = "sonnet" }
env = { GIT_AUTHOR_NAME = "Gas City worker", GIT_AUTHOR_EMAIL = "gc-worker@localhost", GIT_COMMITTER_NAME = "Gas City worker", GIT_COMMITTER_EMAIL = "gc-worker@localhost" }
```

It has to be a city-level `[[patches.agent]]` with `dir` set to the rig. A rig-level `[[rigs.patches]]` block looks like it should work, but it can only reach agents that came from the rig's packs, and implicit agents don't. It fails with `overrides[0]: agent "claude" not found in pack`. The 1.4.2 source holds back city-level patches aimed at implicit agents until after those agents exist, which is why this form works.

In 1.4.2 the built-in Claude provider defaults to `effort = "max"` and bypass permissions. Valid effort values run from `low` to `max`. `sonnet` maps to `--model claude-sonnet-5`, and `haiku`, `opus` and a few pinned versions are also accepted. The `env` line gives the worker's commits their own author so you can tell them apart from yours in `git log`.

Keep `ready_delay_ms = 0` under each `[providers.*]` table where `gc init` put it. `[workspace]` has no such field, and without it the Claude provider waits 10 seconds before it treats each session as ready.

Validate right after saving:

```bash
gc config show --validate
gc doctor | grep -E 'config|✗'
```

Don't skip this. A `city.toml` that fails to load does more than block new sessions. Running workers call `gc bd` to update their beads, and those calls fail too until the file loads again. On the first install that stalled a worker partway through its job.

To check the patch landed, look at the merged config. `gc config explain` doesn't print `option_defaults` for agents in 1.4.2, so use `show`:

```bash
gc config show | grep -n -B4 -A3 'option_defaults'
```

Patches only apply to sessions that start after the change. A worker that's already running keeps its launch flags until it's retired.

### Give workers their own Claude config

The patch above changes the model and effort, but the worker still loads your personal `~/.claude`. That includes your user-level `CLAUDE.md` rules, skills, plugins, status lines and MCP servers. Claude Code reads its config from whatever directory `CLAUDE_CONFIG_DIR` points to, so giving workers a separate one keeps your setup out of them. Their behavior then comes from Gas City and the rig, which is what you want to see before you build on it.

Gas City's own pieces don't live in that directory, so they keep working. In 1.4.2 it passes its hooks through `--settings ~/city/.gc/settings.json` on the launch command, and it installs pack skills into the rig's own `.claude/skills` folder.

Create the directory and set it up once by hand. A fresh Claude config has none of the answers a worker can't give on its own, and each unanswered prompt kills the session the same way the trust prompt did in step 5.

```bash
mkdir -p ~/.claude-gc-worker
cd ~/scratch
CLAUDE_CONFIG_DIR=~/.claude-gc-worker claude --dangerously-skip-permissions
```

Answer everything it asks, which on a fresh directory can include a theme choice, a login, the folder trust prompt and a warning about bypass permissions mode. Log in with the same account you use now. Then type `/exit`. For every rig you add later, run the same `claude` command once in that rig so the new config trusts it too.

If you want workers to follow a few rules of their own, put a short `CLAUDE.md` in `~/.claude-gc-worker`. Keep it small. It applies to every worker that uses this directory. A lean claudeup profile is another way to manage what goes in there.

Add the directory to the agent patch's `env`. Use the full path, since Gas City passes the value as written and `~` won't expand:

```toml
[[patches.agent]]
dir = "scratch"
name = "claude"
option_defaults = { effort = "medium", model = "sonnet" }
env = { CLAUDE_CONFIG_DIR = "/Users/markalston/.claude-gc-worker", GIT_AUTHOR_NAME = "Gas City worker", GIT_AUTHOR_EMAIL = "gc-worker@localhost", GIT_COMMITTER_NAME = "Gas City worker", GIT_COMMITTER_EMAIL = "gc-worker@localhost" }
```

Claude Code also writes session transcripts under the config directory, and `gc session logs` only looks in `~/.claude/projects/` by default. Add the new location near the top of `city.toml` so `gc session logs` still finds worker transcripts:

```toml
[daemon]
observe_paths = ["/Users/markalston/.claude-gc-worker/projects"]
```

Validate again with `gc config show --validate`. The change applies to the next worker session, not one that's already running.

The quickest check is `gc session peek` on the next worker. The status area at the bottom should no longer show your personal status lines (the token-ledger, context-lens and quota-meter lines). `ls ~/.claude-gc-worker/projects` should also gain an entry for the rig once the worker has run. If the session loops in `start-pending` instead, check `start-stderr.log` as in the troubleshooting table. The most likely cause is a first-run prompt the manual setup didn't answer.

When step 7 validates, route the first job with [recipe 1](recipes/01-first-job.md).

## Stopping and removing

```bash
gc stop ~/city
```

This stops every session and the Dolt server, and unregisters the city from the supervisor, so it won't start again at login. Run `gc register` to bring it back.

After a `brew upgrade gascity`, run `gc service restart` so the supervisor picks up the new binary.

To remove Gas City completely:

```bash
gc stop ~/city
brew uninstall gascity
brew untap gastownhall/gascity
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `error: pathspec '...' did not match any file(s) known to git` | The Oh My Zsh `gc` alias is still active | Step 2, then open a new tab and check `type gc` |
| `unalias gc` worked but the next pasted line still ran Git | Zsh expanded the alias when it read the paste | Run the line again on its own |
| `startup is blocked by Dolt author identity` | No Dolt `user.name` or `user.email` | Step 3, then `gc start` from `~/city` |
| `not in a city directory (no city.toml or .gc/ found)` | Running `gc` from outside `~/city` | `cd ~/city`, or pass `--city ~/city` |
| `remote import ... is not installed (missing packs.lock)` | Rig packs not downloaded | `gc import install` from `~/city` |
| `bd show` says `no issue found` for an `sc-` bead | Looking in the city store instead of the rig's | `gc bd --rig scratch show <id>` |
| A rig session sits in `start-pending` or `creating`, and `gc session list` shows a new ID every few seconds | The session dies on startup and the pool keeps replacing it | Run `gc supervisor logs` and look for `session died during startup`. The `last pane output` shows what Claude printed, and the full text is in `~/city/.gc/sessions/<session>/start-stderr.log` |
| That log shows "Quick safety check: Is this a project you created or one you trust?" | Claude Code hasn't been told to trust the rig folder | Run `claude` once in the rig directory, choose _Yes, I trust this folder_, then `/exit` |
| Workers loop again right after adding `CLAUDE_CONFIG_DIR` | The new config directory hasn't answered a first-run prompt (login, trust or the bypass-permissions warning) for this rig | Run `CLAUDE_CONFIG_DIR=~/.claude-gc-worker claude --dangerously-skip-permissions` in the rig, answer the prompts, then `/exit` |
| `gc session logs` finds nothing for a worker | Its transcripts are under the worker config directory | Add `<dir>/projects` to `[daemon] observe_paths` |
| `applying rig patches: ... agent "claude" not found in pack` | A `[[rigs.patches]]` block aimed at an implicit agent | Use a city-level `[[patches.agent]]` with `dir` and `name` (step 7) |
| `unknown flag` for a flag the docs mention | The docs are ahead of your installed version | `gc <command> --help` |
| `dolt circuit breaker is open: server appears down` | Dolt stopped answering for a moment | Wait a minute, then `gc beads health` from `~/city` |
| A hello world job takes about 20 minutes and costs several dollars | The worker runs Opus at `--effort max` with your `~/.claude` rules, skills and Git identity | Step 7: patch the agent and give it its own `CLAUDE_CONFIG_DIR` |
| A running worker stalls, and its `gc bd` calls fail | `city.toml` no longer loads | `gc config show --validate`, fix what it reports, then check the worker with `gc session peek` |
| A worker's job breaks after you switched branches or committed in the rig | The default worker has no worktree. It checks out its bead's branch in the rig itself | Leave the rig checkout alone while a worker has it. Follow the worker with `gc session peek` |
| `gc hook: agent not specified` | Running a worker's command in your own shell | Don't. Use `gc session peek` to follow the worker |
| `zsh: no such file or directory` on a `bd show` line | A literal `<bead-id>` placeholder was pasted, and zsh read `<` as a redirect | Replace it with the real ID from `sling` |

## Next steps

Tutorials 05 (formulas) and 07 (orders) in `docs/tutorials` of the [gascity repo](https://github.com/gastownhall/gascity) cover what you'll need to port the epic loop. Check out the `v1.4.2` tag (or whatever `gc version` says) before reading them, so the examples match your binary. The role prompts under `scratch/gc.*` are worth reading first, since some of them may cover parts of the loop already.
