# Session-service protocol example

This is a fictional documentation-only round, not an implemented service or live Git history.
All commit IDs, PR references and verification outcomes in the fixture are illustrative. The spec
and packet digests are genuinely computed from the included bytes. No API behavior has been tested.

The project already approved [the target](architecture/target.md). Its
[frontier](backlog/frontier.md) assigns one task to document that target in a consumer-facing
[response table](docs/responses.md). Configuration is in `.agent/config.toml`; local policy is in
[the agent policy](docs/agents/policy.md). These files illustrate paths independent of docs/todo.md.

## Walk through a round

1. Takeoff reads the target, frontier, policy and Git/PR state. It learns TASK-001 is active and the
   illustrative result awaits review; it does not infer the service has been implemented.
2. Planning pinned a fictional base and saved [the spec](round-example/specs/A1.md) and
   [packet](round-example/prompts/A1.md), with computed digests in
   [round.toml](round-example/round.toml).
3. Execution returned [an attempt result](round-example/results/A1-1.json) and the response table.
   The gate evidence is explicitly [a fixture](round-example/evidence/A1-1.md), not a real test run.
4. Review compares the table against the approved target, verifies actual checks at the real PR head,
   and records its decision. The fixture stops at `result-ready`; it has not reached merge-ready.
5. After real approval and serial merge, reconciliation would update the canonical item and record
   the final main SHA, documentation behavior delta and the still-unimplemented runtime as a residual.
6. Handoff points to that durable evidence. A fresh planner should select a separately accepted
   implementation item, not mistake this documentation task for an implemented endpoint.

`round-example/` is a tracked teaching fixture. Real runs live under ignored `.agent-runs/`.
`frontier.snapshot.json` is a normalized teaching export, not another editable status authority.
The configured `git diff --check` is a docs whitespace gate; semantic acceptance needs independent
review. A production implementation task would configure meaningful behavior tests as well.

## Recovery exercise

Without any chat transcript, inspect these files and answer: Which task is assigned? Which head and
attempt await review? What do the gate results actually establish? Who may merge? What is the next
permitted action? A correct answer cannot mark the round closed or claim session expiry works.

Use the parent pack's [command catalog](../../docs/agents/README.md) when trying the procedure in a
separate real repository. Do not dispatch this fixture's fake revisions or PR into a runner.
