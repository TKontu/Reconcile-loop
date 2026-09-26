# One documentation round

This walkthrough illustrates a project whose architecture already specifies that expired sessions
receive 401 before resource lookup. TASK-1 asks only for a consumer-facing response table. Runtime
implementation is outside scope. No SHA, PR or test outcome below is an actual result.

## Prepare

Adopt the pack with bootstrap. The project supplies its own architecture and backlog, configures
`git diff --check` as this documentation task's gate, and names an independent reviewer. The planner
refreshes a clean main and writes a complete spec under ignored `.agent-runs/spec.md`.

```sh
python3 scripts/round.py init R1 --base main
python3 scripts/round.py assign R1 A1 --item TASK-1 --branch docs/session-responses --spec .agent-runs/spec.md
python3 scripts/round.py status R1
```

Deliver `.agent-runs/R1/prompts/A1.md` and its manifest digest to an executor in a separate checkout
of the recorded base. The executor documents expired/malformed 401 responses, normal valid-session
lookup and the information-disclosure boundary. It runs the assigned checks and opens an authorized
PR. A whitespace gate proves formatting only; the reviewer must verify the wording against the target.

## Review and integrate

The executor fills `templates/result.json` with actual values and sends it back. The planner imports
it into the coordinator checkout. Results are archived as `results/A1-1.json`, `A1-2.json`, etc.

```sh
python3 scripts/round.py record R1 --result /path/to/submitted-result.json
```

The reviewer checks the current PR head, packet scope, wording and actual gate evidence. A correction
requires a new result and refreshed review. After the designated merger performs the actual merge,
fetch/fast-forward main and record its full merge commit and reviewed head:

```sh
python3 scripts/round.py resolve R1 A1 --outcome merged --head FULL_REVIEWED_HEAD --merge FULL_MERGE_SHA --evidence "Actual review and merge references"
```

The uppercase values are placeholders; do not execute them unchanged. `resolve` records a verified
external action—it does not merge or authorize it. If the worker stops without completing, use
`--outcome cancelled --evidence "reason and remaining-work reference"` instead.

## Reconcile and restart

Mark TASK-1 complete only after its actual acceptance passes. State that runtime expiry remains
unimplemented. Commit a short `docs/rounds/R1.md` with the outcome, evidence, residual and next item;
get required review/merge for that record update. Run the final main gate, write a handoff naming
that full SHA, and confirm no worker holds resources. Then:

```sh
python3 scripts/round.py close R1 --main main --reconciliation docs/rounds/R1.md --handoff HANDOFF.md --evidence "Actual final revision check reference"
```

A new round is refused until this succeeds. Stop the planner session. A fresh planner must recover
the outcome, remaining runtime work and next permitted action from the repository/PRs alone.

This is enough for a human or agent to drive the loop; there is no supervisor process to install.
