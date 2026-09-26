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

## Adopt it

Bring your own architecture, README and backlog. Ask an agent to follow
[bootstrap](.agent/commands/bootstrap.md). It maps existing paths and verification into
[the config template](.agent/config.example.toml), adapts [AGENTS.md](templates/AGENTS.md), and prepares
one small executable item. Your project need not adopt any particular taxonomy, stack or agent vendor.

The pack contains:

- [A short protocol](SPEC.md) and the eight [phase procedures](.agent/commands/bootstrap.md).
- [Assignment](templates/assignment.md), [result](templates/result.json),
  [item](templates/item.md) and [handoff](templates/handoff.md) templates.
- A standard-library [round CLI](scripts/round.py) for local records and packet/result checks.
- One [worked round](examples/one-round.md).

Copy/merge `.agent/`, `scripts/round.py`, `templates/`, `SPEC.md` and `examples/one-round.md`,
preserving their relative paths.
Keep your project's README and merge its operating contract from the template. Optional entry points
are one `.agents/skills/reconcile-loop/` skill and eight `.claude/commands/` wrappers. All use the same
canonical procedures. If your runner does not discover them, read the procedure directly as a prompt.
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
