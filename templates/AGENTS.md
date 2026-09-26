# Project agent contract

Architecture and the sole backlog registry are named in `.agent/config.toml`; read complete linked
item details and the architecture sections needed for the assignment. Handoffs are advisory.

The planner owns selection, dependencies, assignment, shared resources and reconciliation. Executors
own only assigned code/records and work in isolated checkouts at the pinned base. Preserve unrelated
work; never force-push. Return target/scope conflicts to planning; make routine authorized choices.

For behavior changes show the intended failing test, implement the smallest fix and run targeted
checks. Use the configured local gate and assigned integration/live checks in their permitted
safe environments. A skipped check is not a pass. Review relevant callers, data boundaries and scale.

Before publication inspect the diff for defects, secrets and private material. PRs record assignment
identity, head, actual verification and residuals. The designated reviewer checks the current head and
merge authority; executors do not self-merge. Existing user authorization remains valid within scope.

After integration, verify combined state, reconcile observed outcomes into canonical records and
write a bounded handoff. Start the next round with fresh context only after reconciliation closes the
previous one. Use SPEC.md and `.agent/commands/` for phase contracts. No conversation is project memory.
