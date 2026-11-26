# Project agent contract

Architecture and the sole backlog registry are named in `.agent/config.toml`; read complete linked
item details and the architecture sections needed for the assignment. Handoffs are advisory.

The planner owns selection, dependencies, assignment, shared resources and reconciliation. Executors
own only assigned code/records and work in isolated checkouts at the pinned base. Preserve unrelated
work; never force-push. Return target/scope conflicts to planning; make routine authorized choices.

For behavior changes show the intended failing test, implement the smallest fix and run targeted
checks. Use the configured local gate and assigned integration/live checks in their permitted
safe environments. A skipped check is not a pass. Review relevant callers, data boundaries and scale.

- **Local gate first:** run the configured gate locally before every PR. CI is a minimal backstop
  (for example offline unit tests and a whitespace check), never the verification; green CI does not
  show that a live, private-data or model path was exercised.
- **Done means seen:** a behavior is done only with `seen: <run id or artifact path>`. Merged but
  never exercised (flag off, stage not run against real input) stays partial and names the run that
  will show it.
- **Connections:** a new public symbol names its production caller, or is "unwired by design" with
  the item that wires it.
- **Scale:** loops over large inputs bound memory, batch, transaction and concurrency sizes and any
  paid usage, or record the untested bound as a residual.
- **Absent data is reported:** private data, databases and `.env` are absent from fresh checkouts.
  An assignment names where each comes from; a check skipped for lack of them, or of network or a
  service, is reported as skipped.
- **Who judged what:** call a judgment "expert" only when a named expert made it; anything a model
  produced is "LLM-built". Quote a figure only with its basis: population, metric, reference and
  who built it.
- **Flags have a lifecycle:** each flag names the condition that removes it; a shortcut is recorded
  as debt with its follow-up item.
- **No silent design changes:** an architecture or policy change needs a recorded decision in the
  configured decisions record; never smuggle one through implementation.

Before publication inspect the diff for defects, secrets and private material. PRs record assignment
identity, head, actual verification and residuals. The designated reviewer checks the current head and
merge authority; executors do not self-merge. Existing user authorization remains valid within scope.

After integration, verify combined state, reconcile observed outcomes into canonical records and
write a bounded handoff. Start the next round with fresh context only after reconciliation closes the
previous one. Use SPEC.md and `.agent/commands/` for phase contracts. No conversation is project memory.
