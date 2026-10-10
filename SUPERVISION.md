# Supervised rounds

This branch, `autonomous-reconcile-loop`, extends [the protocol](SPEC.md) so a deterministic
supervisor can drive rounds unattended. Main remains the lean manual workflow; this branch is a
superset of it and receives main by merge. Everything here is additive: a round created without
`--supervised` is a version 1 round with the same records and rules as on main; it also takes the
round lock described under Concurrency.

> Status: draft. The ledger records below exist; the supervisor that uses them is not built yet.

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

## Planned

Sessions and halts (`session start|ack|end`, `halt`, `clear-halt`), the supervisor
(`scripts/supervise.py`), role contracts, merge policy and reconciliation automation follow in later
changes on this branch.
