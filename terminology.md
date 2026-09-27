# Terminology

[How the pieces of Gas City connect](./connect-the-dots.html)

Gas City's names come from four families of metaphor. Most confusion comes from the families being mixed, so here they are grouped. The last column ties each term to something from your install where there is one.

**Mad Max (the setting).** Gas Town is the fuel outpost in _Mad Max: Fury Road_, and several names follow that world.

| Term | In the metaphor | In Gas City | In your install |
| --- | --- | --- | --- |
| Gas Town | The fuel outpost | The original orchestrator, now shipped as a pack | Template 3 in `gc init` |
| Gas City | A bigger settlement | The SDK that runs any shape of agent team | `~/city` |
| Rig | The War Rig tanker that hauls the cargo | A Git repo the city works in | `~/scratch`, prefix `sc` |
| Convoy | Vehicles traveling together | A bead that groups other beads and tracks them | `sc-mlb`, the input convoy for your task |
| Polecats | Crew swinging from poles on the War Rig | Throwaway pool workers you rarely look at | `scratch/claude-1` played this part |
| Wasteland | The desert outside | Yegge's public board for sharing work between Gas Towns | Not part of your setup |

**The town hall (civic roles).**

| Term | In Gas City | In your install |
| --- | --- | --- |
| City | The whole deployment: config, packs, stores, supervisor | `~/city` |
| Mayor | The planning agent you talk to, which creates beads and starts workflows | Session `ci-otm` in `~/city` |
| Crew | Long-lived named agents, the "lights on" workers you talk to directly | Not in the default template |
| Mail | Messages between agents, and between agents and you | Dashboard _Mail_ tab |
| Orders | Standing orders that fire a formula on a schedule or event | `nudge-on-route`, `beads-health` |

The Gastown pack adds more roles. The command map says much of the Deacon's job now lives in the supervisor. The Refinery is tied to the merge queue. Dogs are small helpers, usually exec orders in the core pack (for example `mol-dog-stale-db`). The Witness is from Gas Town too. These docs don't say what it does.

**Chemistry (MEOW, "Molecular Expression of Work").** This is the family behind most of the work-tracking words.

| Term | In the metaphor | In Gas City | In your install |
| --- | --- | --- | --- |
| Bead | The smallest unit | One tracked item of work, a row in Dolt | `sc-omn` |
| Formula | A recipe | A reusable template for a unit of work | `mol-do-work` |
| Cook | Making something from a recipe | Turning a formula into beads (`gc formula cook`) | Happens inside `gc sling` |
| Molecule | Atoms bonded together | A formula turned into linked beads under the v1 compiler | Your run was v1 |
| Workflow | | The v2 name for the same graph of beads | `sc-33w` |
| Pour, liquid | Liquid phase | Write every step as its own bead so a crashed run can resume | A `pour = true` formula |
| Vapor, wisp | Gas phase | A lightweight run with only the root bead written | A `phase = "vapor"` formula |

The `mol-` prefix on formula names is short for molecule.

**Hauling work (the verbs).**

| Term | In Gas City | In your install |
| --- | --- | --- |
| Sling | Throw a task or formula at an agent | `gc sling scratch/claude "..."` |
| Hook | Where work hangs until an agent claims it | The worker ran `gc hook --claim` |
| Nudge | Poke a live session with a message | `gc session nudge`, the `nudge-on-route` order |
| Drain | Let a session finish its current work before it stops | `--drain-ack` in the hook call |
| Handoff | Pass a session's context on to a fresh one | `gc handoff` |

Some terms are plain software words with no metaphor behind them: supervisor, controller, reconciler, provider, session, pool, pack, patch, and Dolt. Yegge's "dark factory" and "light factory" are his framing for how visible unattended agents are, not Gas City commands. In [Welcome to Gas City](https://yegge.ai/essays/welcome-to-gas-city/) (2026-04-24) he defines a dark factory as "any system in which coding agents are set up to work autonomously without humans watching," and calls Gas City "a Light Factory… or at least, a very well-lit dark one!" because it is built for observability. And the "Mustering…" you saw in `gc session peek` was Claude Code's own spinner text, not Gas City's.
