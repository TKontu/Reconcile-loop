# Supervised rounds

This branch, `autonomous-reconcile-loop`, extends [the protocol](SPEC.md) so a deterministic
supervisor can drive rounds unattended. Main remains the lean manual workflow; this branch is a
superset of it and receives main by merge. Everything here is additive: a round created without
`--supervised` is a version 1 round with the same records and rules as on main; it also takes the
round lock described under Concurrency.

> Status: draft. The ledger records below exist. The supervisor observes and decides but performs
> no effects yet: it cannot launch agents, push, publish or merge.

## Authority

- Autonomy never grants authority. Merge, reconciliation and new-round permissions come only from
  committed project policy; a supervisor setting can lower them, never raise them.
- Agents never write the ledger, push, open PRs, publish verdicts or merge. Supervisor code does, after
  verifying each claim (head SHA, worktree, PR state, required checks) itself.
- Unknown is never success: an unavailable API, a missing check or a timed-out process stops or holds
  the round; it is not treated as a pass.

## Version 2 ledger

`round.py init ROUND --base REF --supervised` writes `"version": 2` with empty `sessions` and `halts`
records. Lean main's `round.py` refuses version 2 rounds, because it does not enforce their invariants.
Version 2 rounds keep the five assignment states; the additions are fields and append-only records.

### Ownership

`assign` on a supervised round requires one or more `--owns GLOB` relative path patterns and accepts
`--resource NAME` (repeatable) and `--kind work|reconcile`. Owned paths, resources and kind are written
into the packet, so the packet digest binds them. Patterns must be normalized, with no leading or
trailing `/` and no empty, `.` or `..` segments, so one path has one spelling. Two live work
assignments may not share a resource or have owned patterns whose literal prefixes (text before the
first `*`, `?` or `[`) overlap; the check is deliberately conservative.

A `reconcile` assignment needs `--start REF` (recorded as `Start-SHA`), may be created only after every
work assignment is merged or cancelled, and ends the round's work: no further assignments are accepted
while it is not cancelled.

### Reviews

```sh
python3 scripts/round.py review ROUND A1 --head FULL_HEAD --verdict ready|needs-fix|blocked \
  --evidence REFERENCE --reviewer NAME
```

A review is recorded against the latest result and its exact head. A newer result supersedes it. On a
supervised round, `resolve --outcome merged` requires the latest review of the latest result to be
`ready` for the supplied `--head`.

### Closure

Supervised `close` requires `--delta changed|none`, the round's actual behavior change, recorded as
`behavior_delta`. Repeated `none` rounds are the supervisor's stall signal.

### Concurrency

Every command except `init`, including `status`, takes an exclusive lock on
`.agent-runs/ROUND/round.lock` for its duration, in version 1 and 2 rounds alike, so an operator's
command and the supervisor cannot lose each other's updates. This is a single-host lock, not
distributed coordination.

### Sessions

Every launched agent process is recorded before launch (write-ahead), so a restarted supervisor can
find it again instead of dispatching twice:

```sh
python3 scripts/round.py session start ROUND --role planner|executor|reviewer|merger \
  [--assignment A1] [--head FULL_HEAD] --runner NAME --session-uuid UUID --cwd PATH \
  --deadline YYYY-MM-DDTHH:MM:SSZ [--procedure NAME]     # prints {"session": "S1"}
python3 scripts/round.py session ack ROUND S1 --pid PID
python3 scripts/round.py session end ROUND S1 --state exited|timed-out|killed|lost \
  [--exit-code N] [--cost-usd X] [--imported results/A1-1.json]
```

A session is `launching`, then `running`, then ended. At most one live session exists per assignment
and one live planner per round. Role rules: an executor needs an `assigned` assignment or a
`needs-fix` review of the latest result (a repair); a reviewer needs the latest result's head and no
review of it yet; a merger needs a `ready` review of that head. `review --session S` accepts only a
finished reviewer session for the same assignment and head. Cancellation refuses while the
assignment has a live session; a merged resolution tolerates only its live merger session. Closure
refuses any live session. A merger session has no process: it is the write-ahead record of a merge
attempt, which the supervisor verifies by observation before resolving.

### Halts

```sh
python3 scripts/round.py halt ROUND --code CODE --detail TEXT --action TEXT \
  [--assignment A1] [--session S1] [--inventory inventory.json]
python3 scripts/round.py clear-halt ROUND H1 --evidence TEXT
```

A halt records a condition that cannot be recomputed from the ledger and observations: a lost or
timed-out session, invalid agent output, a failed push, publish or merge, a red final gate, or a
planner reporting no executable work or an owed decision. The inventory lists live sessions,
worktrees and resources at that moment. While any halt is uncleared, no session may start and the
round cannot close. Only an operator clears a halt, with evidence of what was inspected or resolved.

## Supervisor (read-only preview)

`scripts/supervise.py` is a stateless loop manager. Each tick it observes the ledger (through
`round.py status`), Git, PR and check state (through `gh`; any failure is Unknown) and session
processes, then a pure `decide()` picks exactly one next action. In this version it only reports:

```sh
python3 scripts/supervise.py next              # one decision as JSON; writes nothing
python3 scripts/supervise.py status            # round, assignments, sessions, halts, decision
python3 scripts/supervise.py run --dry-run     # log decisions; poll while waiting
```

Add `--new-round` to let a level 1 or 2 supervisor propose one new round. `--autonomy N` can only
lower the level. Exit codes: 0 action, wait or routine park; 10 needs attention (halt, hold, stop,
stall or budget); 11 transient or unknown observation; 2 configuration; 3 another instance holds
`.agent-runs/supervisor/lock`. `run` appends each decision to `.agent-runs/supervisor/log.jsonl`
and keeps the latest in `last.json`; it stops at the first decision that needs an effect.

### Configuration

Copy [the example](.agent/supervisor.example.toml) to `.agent/supervisor.toml` and commit it. The
supervisor reads it from the remote default branch (`git show REMOTE/BRANCH:...`), never from the
working tree, so an agent cannot raise its own authority by editing it. An ignored
`.agent/supervisor.local.toml` may override `[runner]` and `[budgets]` keys only. Unknown keys fail.
Level 2 needs `policy.merge.auto_merge` and non-empty `required_checks`; level 3 also needs
`policy.reconcile.auto_reconcile` and `allow_reconcile_merge`. A missing grant exits 2 naming it.

### Decision rules

First match wins: more than one open round stops; a version 1 round is parked as manual; live
sessions are contained even while halted (kill past deadline, mark lost, acknowledge); an uncleared
halt parks; a dirty coordinator checkout or one with commits not on the remote default stops; an
unfetched remote head asks for a fetch; exited sessions are imported and in-flight merges verified.
Without an open round the supervisor parks on stall (`stop.stall_rounds` closed rounds with delta
`none`), run limit or autonomy below 3 unless `--new-round`, else proposes the next round at the
remote default head. A round without assignments launches one planner. Each idle assignment then
yields at most one candidate, chosen as Merge > LaunchReviewer > LaunchExecutor > Cleanup within
`max_parallel` and the round budget; a hold on one assignment never blocks another:

| Assignment | Decision |
| --- | --- |
| `assigned` | launch executor |
| `blocked` result | hold |
| result, PR missing, closed, merged externally or head moved | hold |
| result, no review of its head | launch reviewer |
| `needs-fix` | launch repair executor, or hold after `stop.max_repairs` |
| review `blocked` | hold |
| `ready`, level 1 | park awaiting a person's merge |
| `ready`, level 2+ | merge gate: merge, wait for checks, or hold |
| `merged`/`cancelled` with a worktree | clean up, or hold if the worktree is dirty |

When every assignment is terminal, levels 1 and 2 park awaiting reconciliation; level 3 creates a
reconcile assignment from the remote head, runs the final gate after it merges and closes the round.

### Merge gate

All must hold: the latest review is `ready` for the latest result head; the PR is open, not a
draft, at that head, from the assigned branch into the default branch, `MERGEABLE` and `CLEAN` or
`HAS_HOOKS`; every `required_checks` name succeeded on that exact SHA (newest run wins; missing,
skipped, neutral and cancelled fail; pending past `ci_timeout_minutes` after the review holds); every
changed path is inside the owned globs and outside `protected_paths`; the change is within
`max_changed_lines` and has no binary files; a reconcile assignment also needs
`allow_reconcile_merge`. A branch behind or conflicting with the default branch holds; the supervisor
never updates branches or bypasses protection.

## Planned

Launching agents, importing their output, publishing reviews, merging and reconciliation follow in
later changes on this branch.
