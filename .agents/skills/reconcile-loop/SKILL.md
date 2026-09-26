---
name: reconcile-loop
description: Bootstrap or run an architecture-constrained development round with bounded assignments, review, merge and reconciliation.
---

# Reconcile-loop

Read the target project's AGENTS.md and `.agent/config.toml`, then the selected phase below.
Resolve packaged links relative to this skill file. User scope and existing authorization govern
external actions; this skill does not independently grant publication or merge permission.

- [Bootstrap](../../../.agent/commands/bootstrap.md): adopt the workflow and configure actual paths/gates.
- [Takeoff](../../../.agent/commands/takeoff.md): orient a fresh planner without selecting work.
- [Plan](../../../.agent/commands/plan-round.md): choose executable work and create packets.
- [Execute](../../../.agent/commands/execute-task.md): complete one isolated assignment and return evidence.
- [Review](../../../.agent/commands/review-round.md): evaluate actual candidate heads.
- [Merge](../../../.agent/commands/merge-round.md): integrate accepted authorized changes serially.
- [Reconcile](../../../.agent/commands/reconcile.md): record observations and close the round.
- [Handoff](../../../.agent/commands/handoff.md): prepare a bounded delta for the next fresh session.

For an end-to-end request, follow these phases in order within the granted scope. Stop at unresolved
approval or acceptance gates; continue independent authorized work when possible. This pack supplies
local scaffolding, not an unattended agent launcher. Do not substitute its contributor contract for
the adopting project's operating contract.
