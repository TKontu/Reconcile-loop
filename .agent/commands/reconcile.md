# reconcile

Follow [the shared contract](common.md).

Input: explicit round ID and final integration state.

Refresh the final default-branch revision and inspect the actual merged/remaining PRs. Run configured
combined-state verification on that revision. A failed or unavailable required gate keeps the round
open with a recovery owner; record findings even when closure is blocked.

For each item read acceptance and actual evidence before changing its status. Route observed results:
acceptance met to its outcome record; newly exposed work to planner-owned backlog items; negative
measurements to reports; divergence through the authorized deviation process; target changes to
non-executable proposals until approved. Do not silently change the target to fit an implementation.
Retain untested operating envelopes and owed verification. Apply answered decisions explicitly.

Update canonical dependencies/frontier and write [the reconciliation record](../../templates/reconcile.md).
Keep status single-valued and link canonical decisions. Preserve dated superseded rulings/measurements;
ordinary replaced prose already has Git history. Record actual production behavior delta.

Use [handoff](handoff.md) once durable records are complete. Close only when required gates and outcome
recording are satisfied. Report remaining blocked work and the next exact action; do not start a new
round in the old session or allocate executor-owned work implicitly.

Enforce [protocol closure](../../SPEC.md): account for merged/cancelled assignments, release confirmed
idle resources, persist final SHA, reconciliation/handoff references and closure evidence. Never begin
a new round from an unreconciled predecessor.
