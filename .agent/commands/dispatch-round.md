# dispatch-round

Follow [the shared contract](common.md).

Input: explicit round ID and dispatch authority from the user or established project policy.

Read [supervision](../../docs/supervision.md) and the round's immutable packets. Preflight every target:
base/digest, clean separate workspace, branch/record ownership, required artifacts, resource access,
runner availability, and explicit assignment-to-runner mapping. Resolve all errors before sending.

When available and authorized, send each packet unchanged to its mapped executor; policy context is
separately versioned. Record each dispatch acknowledgement and session/process identity immediately.
Otherwise provide packet paths or complete inline packets for manual delivery; mark awaiting dispatch,
not running. Do not invent runner commands or launch overlapping work in a shared checkout.

Wait only within configured deadlines. Check runner status and expected PR metadata/checks separately.
A settled worker is not proof of completion. On partial failure stop new sends, inventory active work,
and use [resume-round](resume-round.md); do not replay the batch or release a live worker's resources.
Output per-assignment state, PRs, pending checks, and concrete blockers. No merge authority is implied.
