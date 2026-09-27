# Gas City runbook

Operating notes for [Gas City](https://github.com/gastownhall/gascity), the orchestrator that routes beads of work to coding-agent sessions running in your Git repos. These notes take a Mac from nothing to a city with a tuned Claude Code worker, then cover routing, watching and merging its jobs, and adding a real project as a rig.

Written against **Gas City 1.4.2** and **bd 1.3.0** on macOS, from a first install and a first real rig (coderay). Steps say what they printed on that build. The gascity docs track `main`, which runs ahead of the Homebrew release, so re-check after `brew upgrade gascity`.

## Why this exists

A default city runs your personal Claude Code setup at maximum effort, dies in a restart loop on first-run prompts, and leaves commits under your name in branches you didn't expect. These notes are the short path around it.

## Docs

| File                                                      | Use it when                                                          |
| --------------------------------------------------------- | -------------------------------------------------------------------- |
| [SETUP.md](SETUP.md)                                      | Setting up Gas City on a new Mac, through a tuned worker for one rig |
| [recipes/01-first-job](recipes/01-first-job.md)           | Sending a task to a worker, directly or through the mayor            |
| [recipes/02-watch-a-worker](recipes/02-watch-a-worker.md) | Following a job from the terminal or the dashboard                   |
| [recipes/03-merge-the-work](recipes/03-merge-the-work.md) | A bead closed and you want its branch                                |
| [recipes/04-coderay-rig](recipes/04-coderay-rig.md)       | Adding a repo that already has its own beads store as a rig          |

Reference:

| File                                           | Read it for                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------ |
| [how-gas-city-works.md](how-gas-city-works.md) | The upstream orientation: orchestrator, bead store, six primitives |
| [terminology.md](terminology.md)               | What the Mad Max, civic and chemistry names mean                   |
| [connect-the-dots.html](connect-the-dots.html) | A map of how the pieces connect                                    |

## Scripts

| Script                                           | Does                                                                        |
| ------------------------------------------------ | --------------------------------------------------------------------------- |
| [`scripts/check-links.py`](scripts/check-links.py) | Checks every relative link and `#anchor` in the docs. Run it after moving or retitling a doc |

## Prerequisites

```sh
gc version                  # 1.4.2
bd version                  # bd version 1.3.0 (Homebrew)
claude --version            # installed and signed in
dolt config --global --list # user.name and user.email set (SETUP step 3)
type gc                     # /opt/homebrew/bin/gc, not a git alias (SETUP step 2)
```

Run `gc` commands from `~/city`. Most of them find the city by walking up from the current directory.

## Vocabulary

| Term           | Means                                                                                   |
| -------------- | --------------------------------------------------------------------------------------- |
| city           | The whole deployment: config, packs, stores, supervisor. `~/city`                       |
| rig            | A Git repo the city works in, with its own bead prefix                                  |
| bead           | One tracked unit of work, a row in Dolt. IDs carry the rig prefix, like `sc-omn`        |
| sling          | Create a bead and route it to an agent in one step. `gc sling <rig>/<agent> "<text>"`   |
| formula        | A reusable method for a job. Slinging attaches one, by default `mol-do-work`            |
| session        | A running agent. Pools start and retire them; the work survives in beads                |
| implicit agent | `claude`, `codex`, `gemini`: one per provider, per city and per rig, from no pack       |
| patch          | A `[[patches.agent]]` block in `city.toml` that changes an agent's flags or environment |

More in [terminology.md](terminology.md).

## Five traps

**The Oh My Zsh `gc` alias runs `git commit`.** Until it's gone, `gc sling` fails with `error: pathspec 'sling' did not match any file(s) known to git`. Zsh expands aliases when it reads a pasted block, so `unalias gc` and `gc version` pasted together still run Git on the second line. [SETUP step 2](SETUP.md#2-remove-the-oh-my-zsh-gc-alias).

**Claude's folder-trust prompt kills workers in a loop.** A session has nobody to answer "Is this a project you created or one you trust?", so it dies, the pool replaces it, and `gc session list` shows a new ID every few seconds. `--dangerously-skip-permissions` doesn't cover this prompt. Run `claude` once in every new rig, and again under the worker's `CLAUDE_CONFIG_DIR`.

**An untuned worker is you at maximum effort.** It launches Opus at `--effort max` with your `~/.claude` rules, skills and Git identity. The first hello world took about 20 minutes and cost $4.76. Patch it with a city-level `[[patches.agent]]` and give it its own `CLAUDE_CONFIG_DIR`. A rig-level `[[rigs.patches]]` block can't reach implicit agents. [SETUP step 7](SETUP.md#7-tune-the-rigs-worker-before-the-first-job).

**A `city.toml` that fails to load stalls running workers.** Their `gc bd` calls fail until the file loads again. Run `gc config show --validate` after every edit.

**Stay out of the rig's checkout while a worker has it.** The default worker has no worktree. It checks out its bead's branch right in the rig, so switching branches or committing there pulls the branch out from under it. Watch with `gc session peek`, and don't run the `gc hook` commands you see there.

## Troubleshooting

The symptom-to-fix table is at the end of [SETUP.md](SETUP.md#troubleshooting). The coderay recipe has its own.
