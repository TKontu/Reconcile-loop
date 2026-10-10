# reconcile

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Inspect actual merged/cancelled outcomes and final main. Run the configured verification and any
additional combined-state gates owed by the assignment. Record failures and their owner; failed
required gates keep the round open. Confirm no workers still hold mutable resources.

Update only the canonical backlog/details: acceptance met → completed outcome; newly discovered work
→ new item; negative measurement → evidence; target conflict → proposed decision awaiting approval.
Cancelled work remains visible with its next owner. Do not change architecture to make a result fit.
Record residuals and the actual behavior change, including none for documentation-only work.

Leave durable reconciliation evidence in tracked project state: update existing backlog/details or
decision records with outcomes, evidence, remaining work and next action. The reconciliation PR may
already capture this; do not create a separate report just to close the round. Get any required
review/merge for the record updates and retain a durable evidence reference.
After the final default-branch revision is known, run the owed final gate and write
[the handoff](handoff.md). Close locally:

```sh
python3 scripts/round.py close ROUND --main main --reconciliation "<reconciliation-evidence-reference>" --handoff HANDOFF.md --evidence "Final revision check evidence; workers stopped"
```

Replace the placeholder with an existing tracked file path or an HTTP(S) evidence URL, such as the
reconciliation PR. Use the actual default branch and handoff path. No report-path configuration is
required. The CLI checks terminal assignments, merge ancestry and the handoff SHA. It checks local
evidence files at final main; it records URLs without fetching them. Verify the reference actually
shows this round's reconciliation into tracked state and that all required gates passed before
closing. Only then end the planner session and start a fresh round. Cancelled rounds also reconcile.
