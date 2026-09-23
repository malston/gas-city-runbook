# Setting up Gas City on a new Mac

This runbook takes a fresh macOS machine to a running Gas City with one rig and a first job routed to a Claude Code agent. It's written from a first install of Gas City 1.4.2 and folds in every problem that install hit, so you can run it top to bottom without detours.

Each step says what to expect. If the output differs, check [Troubleshooting](#troubleshooting) before moving on.

## Before you start

Run commands one line at a time, at least until step 1 is done. Zsh expands aliases when it reads a pasted block, before any line in that block runs. A multi-line paste that contains `unalias gc` followed by `gc version` will still run the old alias on the second line.

You'll also need Claude Code installed and signed in, since that's the agent this city uses.

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

Pick _Yes, I trust this folder_, then exit with `/exit`. Do this once for every new rig, before you sling work to it.

## 6. Check the agents

```bash
gc agent list
```

You should see city agents (`mayor`, `claude`, `codex`, `gemini` and some housekeeping ones) and a set of rig agents qualified by the rig name, such as `scratch/claude` and `scratch/gc.implementation-worker`. The `scratch/gc.*` agents are the roles from the pack you just installed.

## 7. Route a first job

From `~/city`, sling a task to the rig's Claude agent. Use the qualified name.

```bash
gc sling scratch/claude "Create a script that prints hello world"
```

Output looks like this:

```text
Created sc-omn — "Create a script that prints hello world"
Attached workflow sc-33w (formula "mol-do-work") to sc-33w
Dashboard: http://127.0.0.1:8372/city/city/runs/sc-33w
```

`sc-omn` is the task bead. `sc-33w` is the workflow the agent follows, taken from its default formula `mol-do-work`.

## 8. Watch it work

The dashboard link from `sling` is the easiest view. It shows each step of the workflow as it moves from pending to running to closed, and the _Session_ tab shows the agent's live session.

From the terminal, go through `gc bd` so the lookup hits the rig's store:

```bash
gc bd --rig scratch show sc-33w --watch
```

Plain `bd show` run from `~/city` looks in the city's own store and reports `no issue found`. Running plain `bd` from inside `~/scratch` also works.

To attach to the agent directly:

```bash
gc session list
gc session attach <session-name>
```

Detach with `Ctrl-b d` so the session keeps running.

When the bead closes, check `ls ~/scratch` for the script and `git -C ~/scratch log` to see whether the agent committed it.

## What to expect on the dashboard

Three things on the first run look odd but are normal.

The run header shows `V1`. `mol-do-work` uses the older formula compiler. Formulas you write should declare `formula_compiler = ">=2.0.0"` to get `check`, `retry` and `drain`.

The _Diff_ tab says no diff is available because the run recorded no `work_dir`. The default worker edits the rig directly without a worktree. A port of the epic loop needs to set up per-bead worktrees itself (see `gc worktree`).

_Health_ may show a badge. Click it before adding more rigs. One likely cause is Dolt running in embedded mode, which makes Gas City fall back to calling `bd` as a subprocess for every store operation. `bd context` should report `dolt_mode=server` for the faster native store.

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
| `zsh: no such file or directory` on a `bd show` line | A literal `<bead-id>` placeholder was pasted, and zsh read `<` as a redirect | Replace it with the real ID from `sling` |

## Next steps

Tutorials 05 (formulas) and 07 (orders) in `docs/tutorials` of the [gascity repo](https://github.com/gastownhall/gascity) cover what you'll need to port the epic loop. The role prompts under `scratch/gc.*` are worth reading first, since some of them may cover parts of the loop already.
