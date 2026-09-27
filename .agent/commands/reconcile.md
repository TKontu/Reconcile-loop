# reconcile

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Inspect actual merged/cancelled outcomes and final main. Run the configured verification and any
additional combined-state gates owed by the assignment. Record failures and their owner; failed
required gates keep the round open. Confirm no workers still hold mutable resources.

Update only the canonical backlog/details: acceptance met → completed outcome; newly discovered work
→ new item; negative measurement → evidence; target conflict → proposed decision awaiting approval.
Cancelled work remains visible with its next owner. Do not change architecture to make a result fit.
Record residuals and the actual behavior change, including none for documentation-only work.

Write and commit a short reconciliation report containing the round ID, each item/outcome, evidence,
remaining work/decisions and next action. Get any required review/merge for these record updates.
After the final default-branch revision is known, run the owed final gate and write
[the handoff](handoff.md). Close locally:

```sh
python3 scripts/round.py close ROUND --main main --reconciliation "<tracked-reconciliation-path>" --handoff HANDOFF.md --evidence "Final revision check evidence; workers stopped"
```

Replace the reconciliation placeholder with the project’s chosen tracked report path; use the actual
default branch and handoff path. No reconciliation-path configuration is required. The CLI requires
terminal assignments, merge ancestry, committed reconciliation and a handoff naming final main. It cannot judge the truth of the report or
whether you omitted a required gate. Review those before closing. Only then end the planner session
and begin the next round with fresh context. A cancelled round also reconciles its partial findings.
