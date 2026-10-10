# Reconcile-loop

A small repo-native workflow for architecture-constrained agent engineering.

> Agents are disposable. Project state is durable.

```text
architecture + current frontier
  → plan → isolated execution → review → merge → reconcile
  → fresh planner → repeat
```

**A round ends when its observations are reconciled into project state, not merely when its PRs merge.**
The architecture defines the target; one backlog records current status and dependencies. Assignments
bound execution, PRs carry evidence, and a fresh planner reconstructs state without previous chats.
Only the next executable frontier needs detailed planning.

## Quick start

For people, from a clean checkout of your project:

```sh
git clone https://github.com/TKontu/Reconcile-loop ../Reconcile-loop
python3 ../Reconcile-loop/scripts/install.py . --claude --codex
```

Then ask your agent to follow [bootstrap](.agent/commands/bootstrap.md) (`/bootstrap` in Claude Code)
and commit the result. Each round runs `takeoff → plan-round → execute-task (one per executor) →
review-round → merge-round → reconcile`. To update, pull the pack, rerun the installer and merge any
`*.pack-new` files.

For agents, paste this prompt:

> Adopt Reconcile-loop in this repository. Clone https://github.com/TKontu/Reconcile-loop into a
> temporary directory, run its `scripts/install.py` against this repository root from a clean
> checkout (add `--claude` and/or `--codex` for the runners in use), then follow
> `.agent/commands/bootstrap.md`. Stop with a ready first item or named setup gaps; do not dispatch,
> publish or merge.

## Adopt it

Bring your own architecture, README and backlog. Ask an agent to follow
[bootstrap](.agent/commands/bootstrap.md). It maps existing paths and verification into
[the config template](.agent/config.example.toml), adapts [AGENTS.md](templates/AGENTS.md), and prepares
one small executable item. Your project need not adopt any particular taxonomy, stack or agent vendor.

The pack contains:

- [A short protocol](SPEC.md) and the eight [phase procedures](.agent/commands/bootstrap.md).
- Optional read-only [status](.agent/commands/status.md) and advisory [PR verdict](.agent/commands/pr-verdict.md)
  helpers.
- [Assignment](templates/assignment.md), [result](templates/result.json),
  [item](templates/item.md) and [handoff](templates/handoff.md) templates.
- A standard-library [round CLI](scripts/round.py) for local records and packet/result checks.
- One [worked round](examples/one-round.md).

Install from a clone or release of this repository into a clean checkout of your project:

```sh
python3 path/to/Reconcile-loop/scripts/install.py path/to/project --claude --codex
```

It copies `.agent/`, `scripts/round.py`, `templates/`, `SPEC.md`, `examples/one-round.md` and the
MIT notice (`.agent/LICENSE`), preserving relative paths, and ignores `.agent-runs/` and HANDOFF.md.
The runner flags are optional and remembered. `.agent/pack.lock` records the pack version and
installed file hashes. Rerun the same command from a newer pack to update: unmodified files are
replaced, while locally edited or pre-existing files are kept with the new version beside them as
`*.pack-new` to merge and delete. It never writes your README, AGENTS.md or `.agent/config.toml`.
Use `--dry-run` to preview. Copying the same paths manually remains supported.
Keep your project's README and merge its operating contract from the template. Optional entry points
are one `.agents/skills/reconcile-loop/` skill, ten `.claude/commands/` wrappers and three
`.claude/agents/` subagents (review lens, CI watcher, quick fixer). All use the same canonical
procedures. If your runner does not discover them, read the procedure directly as a prompt.
Ignore `.agent-runs/` and HANDOFF.md; keep durable findings in tracked records or PRs.

## Run a round

| Phase | Contract |
| --- | --- |
| [takeoff](.agent/commands/takeoff.md) | Reconstruct current state; no selection or mutations |
| [plan-round](.agent/commands/plan-round.md) | Choose executable work and produce packets; no execution |
| [execute-task](.agent/commands/execute-task.md) | Implement in isolation and return evidence; no merge |
| [review-round](.agent/commands/review-round.md) | Verify current heads against scope and acceptance |
| [merge-round](.agent/commands/merge-round.md) | Merge authorized reviewed changes serially |
| [reconcile](.agent/commands/reconcile.md) | Update project truth and close the round |
| [handoff](.agent/commands/handoff.md) | Record a bounded delta for the next fresh session |

Planner decisions remain with the planner; executors own only assigned work. Existing authorization
applies; reserved decisions block dependent work while independent authorized work can continue.

The CLI requires Python 3.11+ and Git. Run `python3 scripts/round.py --help`. It does not launch agents,
run your tests, approve work, contact the PR host, merge branches or manage service locks. Use one
coordinator and run ledger writes serially. Manual packet delivery is supported; unattended
supervision can be added later against the same contracts.

## Maintain this pack

Run `python3 -m unittest discover -s tests` and `git diff --check`. The tests use temporary local Git
repositories; no service, network, third-party Python dependency or agent runtime is required.

Only `main` is maintained. The [expanded experimental snapshot](https://github.com/TKontu/Reconcile-loop/tree/docs/standalone-patterns)
is retained for reference and receives no parallel feature development.

Licensed under the [MIT License](LICENSE). Retain its notice when copying the scaffolding.
