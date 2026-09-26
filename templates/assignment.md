# Assignment <round>/<assignment>

## Identity and delivery
- Base: <full verified main SHA>
- Branch / isolated workspace: <branch and path>
- Spec SHA-256: <computed digest of frozen task-spec bytes, not of this rendered packet>
- Executor: <owner>
- Delivery: <immutable packet path or complete inline packet>

This packet stands alone. Do not require access to the planner's ignored ledger or workspace.

## Authoritative scope
- Backlog row and complete detail: <paths and anchors>
- Architecture sections / approved decisions: <exact references>
- Objective: <one measurable result>
- In scope / non-goals: <explicit boundaries>
- Expected files and symbols: <paths>
- Editable registry/detail records: <exact records or none>
- Sibling ownership / prohibited records: <boundaries>

## Resources and implementation
- Lane / permitted services: <offline, disposable integration, or persistent/live; exact access>
- Exclusive resources / reservation owner: <identities or none>
- Required local artifacts/configuration: <provisioned locations; no secrets>
- Production connections: <callers and producers/consumers, or unwired with follow-up item>
- Scale envelope: <tested/expected cardinality and query, memory, checkpoint bounds, or N/A>
- Verification owner: <who completes every required gate>

## Acceptance and evidence
- Criteria: <observable results>
- RED / expected failure: <command and behavior, or docs-only N/A with reason>
- Targeted GREEN: <commands>
- Local pre-PR gate: <command>
- Integration/live: <exact commands, environment, scope, skip reporting; or N/A with reason>
- Deferred merge-ready gate and owner: <check and triggering procedure>
- Default / frontier impact: <required reporting>

Preserve the pinned base and frozen scope. Return conflicts or missing decisions to planning.
Use the project's PR evidence template. Stop after the PR and required executor checks; do not merge.
