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
unimplemented. Update the existing backlog/details with the outcome, evidence, residual and next item;
get required review/merge for those updates. That reconciliation PR provides durable evidence, so no
separate report is needed. Run the final main gate, write a handoff naming that full SHA, and confirm
no worker holds resources. Then:

```sh
python3 scripts/round.py close R1 --main main --reconciliation "https://example.invalid/project/pull/RECONCILIATION_PR" --handoff HANDOFF.md --evidence "Actual final revision check reference"
```

Replace the illustrative URL with the actual reconciliation PR, or name an existing tracked file
containing the evidence. The CLI does not fetch the URL; the reviewer verifies it.

A new round is refused until this succeeds. Stop the planner session. A fresh planner must recover
the outcome, remaining runtime work and next permitted action from the repository/PRs alone.

This is enough for a human or agent to drive the loop; there is no supervisor process to install.

## Interrupted round with CI unavailable

Suppose a later round has two assignments. A1 is merged; A2 has a PR but its required CI is queued
because runners are unavailable. Verify A1's actual merge and record its merged outcome if it has
not already been recorded. For A2, submit a candidate result with the gate marked `unavailable`;
retain earlier results unchanged. Its evidence names the affected head, the coordinator as recovery owner, and the
next action: restore runner availability and verify that head's required checks. A `blocked`
result with the same details is also appropriate if execution cannot continue.

Write the bounded handoff and end the interrupted session with the round still open. Do not cancel
A2 just to close the round. The replacement planner:

1. Reads the open ledger, original packets, saved results and actual PR/merge state.
2. Checks whether A2's worker survives and who owns its mutable resources; reuses it or confirms it
   stopped and releases ownership before assigning a replacement the unchanged packet.
3. Records an already-completed merge missing from the ledger only after verifying it; never merges
   A1 again or re-executes completed work solely because the session changed.
4. Restores access through the project's authorized operator, runs only outstanding or invalidated
   checks, and imports a new A2 result with actual evidence. A changed PR head requires fresh review.
5. Reviews and merges A2, verifies combined state, reconciles both outcomes and closes the same round.

Runner restoration is project policy, not a CLI capability. No additional round, runtime state or
separate status document is needed for this recovery.
