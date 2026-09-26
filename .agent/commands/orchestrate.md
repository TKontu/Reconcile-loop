# orchestrate

Follow [the shared contract](common.md).

Input: target round/items or maximum parallelism and the user's authorized scope.

Follow [takeoff](takeoff.md), [plan-round](plan-round.md), [dispatch-round](dispatch-round.md),
[review-round](review-round.md), [merge-round](merge-round.md), then [reconcile](reconcile.md).
If a round already exists, inspect and resume its actual phase rather than creating duplicate work.
Each phase's stopping rules and approval requirements still apply. Starting orchestration does not
implicitly authorize every external action or require agents when manual execution is requested.

Preserve separation between implementation and acceptance/merge. Use isolated executor workspaces;
if launch capabilities are unavailable, produce self-contained packets and report awaiting delivery.
Keep the ledger current with observed phase artifacts. Surface required decisions through
[decisions](decisions.md) and continue only independent authorized work.

Stop after one reconciled round and validated handoff, or at a concrete unresolved gate. Repeated
unattended rounds require [supervise](supervise.md) and an implemented lifecycle adapter.
