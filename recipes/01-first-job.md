# 1. Route a first job

Assumes [SETUP.md](../SETUP.md) is done: the city is running, the `scratch` rig is added and trusted, and its worker is tuned.

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

## Or hand it to the mayor

The Gas City README takes a different route. You create the bead yourself and let the mayor decide who works on it. That's closer to how a city is meant to run day to day. Slinging straight to `scratch/claude` is more predictable when you're testing one worker, which is why this runbook uses it first.

Create the bead from inside the rig, so it lands in the rig's store with an `sc-` ID:

```bash
cd ~/scratch
bd create "Create a script that prints hello world"
```

A bead made this way just sits in the store. Nothing routes it until someone slings it. Attach to the mayor and ask it to take care of the bead:

```bash
cd ~/city
gc session attach mayor
```

Tell it something like "Route sc-xxx to a worker in the scratch rig," using the ID `bd create` printed. The mayor ships with a skill for planning, creating beads and starting workflows, so it slings the bead for you. Detach with `Ctrl-b d` and watch the work as in [recipe 2](02-watch-a-worker.md).

You can also skip the mayor and route an existing bead yourself. `gc sling` accepts a bead ID as well as plain text:

```bash
cd ~/city
gc sling scratch/claude sc-xxx
```

The README also runs `gc start` right after `gc init`. In 1.4.2 `gc init` already registers and starts the city unless you pass `--no-start`, so the extra `gc start` is harmless but only needed when `init` stopped early, as it does without a Dolt identity.

To confirm the worker launched with your patched flags, watch for its start command:

```bash
gc events --follow | grep -o '"command":"claude[^"]*"'
```

It should show `--effort medium --model claude-sonnet-5`. This only prints new events, so start it before the `sling` or wait for the next session.

