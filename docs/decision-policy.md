# Standing decision authority

A project can authorize routine engineering choices in advance, avoiding repeated questions without
losing accountability. Adopt this policy explicitly and name its approver, scope and revision in
[the project policy template](../templates/decision-policy.md). This library itself grants no authority.

## Decide within the assignment

When authorized, choose among implementation options that preserve approved scope, architecture,
acceptance and resource limits. Prefer the simplest sufficient solution, reversibility, precise
interfaces and existing capabilities. Record material choices, rationale and the rejected alternative
in the PR. Reversibility does not automatically justify a flag, new abstraction or migration;
alternative paths still need lifecycle gates under [the pattern catalog](patterns.md).

Standing authority does not permit an executor to edit cross-item priorities or expand ownership.
Propose out-of-scope follow-ups to the planner. Architectural divergence follows the project's approved
decision procedure; recording a deviation is not by itself permission to take it.

## Reserve decisions explicitly

The adopting project names actions requiring additional approval, such as target changes, production
default changes, merges requiring independent review, deployments, persistent-data destruction,
spending, or exceptions to safety/quality rules. Identify who can approve each class and where that
approval is recorded. Apply existing session/operator authorization; do not ask again for an action
already authorized within its scope. A supervisor setting cannot override this policy.

## Queue a question; continue independent work

Use [the decision record](../templates/decision.md) for a reserved or genuinely unspecified decision.
Include options, a recommendation, affected item, blocked behavior, owner, and what can proceed
without the answer. Keep the decision in a durable project record and reference it from the backlog;
there must not be a second competing status registry.

Dependent work remains blocked until an explicit answer is recorded. Continue independent authorized
work when possible, without widening scope or inserting speculative scaffolding solely to avoid a
blocker. If nothing can proceed, report the blocker and stop that lane. Asynchronous escalation means
the operator need not answer immediately; it does not mean every assignment can always finish.

## Apply and retain the answer

Record approver, timestamp, scope, chosen option and rationale. The planner updates affected items,
assignments and acceptance, then releases only the work the answer actually unblocks. Executors do
not infer approval from elapsed time, a reminder, or silence. Preserve superseded decisions with a
pointer to the replacement. Serialize queue writes or use separate records to avoid lost updates.
