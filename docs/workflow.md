# Round workflow

Use this with [the pattern catalog](patterns.md). The supervisor handles launch, liveness, and
waiting. The planner makes engineering decisions and reviews results. Executors perform bounded
work. A human operator approves target changes and any actions reserved by local policy.

## 1. Takeoff — orient, then stop

Read the project contract and stable README orientation. Inspect working-tree status, current and
remote revisions, recent merges, open PRs, and the canonical backlog frontier. Do not alter a dirty
workspace during orientation. Classify the optional handoff by its recorded main SHA: equal is
current; an ancestor is stale and requires reading intervening changes; a non-ancestor is invalid.
Missing or invalid handoff is recoverable from Git, PRs, and canonical records.

Output a short brief: purpose, current maturity, open work/conflicts, frontier, handoff freshness,
and next authoritative reads. Selection happens in planning, not implicitly during orientation.

## 2. Plan — choose executable work

Refresh a clean main with a fast-forward-only update and pin one full base SHA. Select only ready
or active items with resolved dependencies and complete acceptance. Read each whole item detail
and its named architecture sections. Verify file and shared-contract claims in source.

Create one [assignment](../templates/assignment.md) per isolated executor. For a batch, record
ownership in [a round manifest](../templates/round.toml); reject branch, record, and exclusive-resource
collisions. Dependent or later-base work belongs in a later round. Provision required ignored
artifacts/configuration securely. Freeze the specs and compute their digests before dispatch.

If scope or architecture is undecided, return it for a decision. Planning fewer independent items
is preferable to pretending blocked work is executable. Do not launch executors merely by writing
a plan; dispatch follows the operator's or established process's authorization.

## 3. Execute — return evidence

Verify the assigned base against fetched main before branching in the isolated workspace. Stop on
drift and request a revised assignment; do not change the pinned SHA yourself. Follow the packet,
inspect callers in source, and use test-first development for behavior changes. Documentation-only
assignments can specify link/consistency checks instead of artificial RED/GREEN tests.

Run targeted checks during development and the configured local gate before the PR. Run required
surgical integration/live checks only in the authorized environment. Record unavailable checks and
skips; never present them as passes. Update only named backlog/detail records when permitted.
Review the diff for secrets and private source references. Open a small PR using
[the evidence template](../templates/pull-request.md), get required executor checks green, and stop.
Executors do not merge their own work.

## 4. Review — evaluate the result against its contract

Read metadata, changed files, and diff first. Match assignment identity, base, and digest. Compare
actual behavior against authoritative scope and acceptance, checking source connections and scale
as described in [the review template](../templates/review.md). Small authorized fixes can remain
on the branch; larger defects or scope changes return to the executor or planner.

Record ready, awaiting fix, or blocked with concrete evidence. Run deferred integration on the
reviewed head when required. A new commit invalidates head-specific checks and affected review;
reverify before merge. Review readiness is not itself permission to merge.

## 5. Merge — integrate serially

The designated reviewer/operator confirms review, exact-head checks, mergeability, and local merge
policy. Respect independent approval requirements when the reviewer also authored fixes. Merge
one accepted PR at a time and refresh main after each. Reassess remaining branches for changed
premises, dependencies, and conflicts. Resolve conflicts deliberately without force-push and repeat
affected verification; never silently treat old evidence as covering a changed implementation.

## 6. Reconcile — close the feedback loop

Run the project's round-end combined-state gate on final main when configured. A failure keeps the
round open with a named recovery owner. Record the final SHA and evidence in
[the reconciliation record](../templates/reconcile.md).

Route every outcome: acceptance met → update status; newly exposed work → backlog item; failed
measurement → evidence report; intentional target divergence → approved deviation; target challenge
→ non-executable architecture proposal awaiting approval. Retain residuals and owed verification.
Update dependencies and the frontier from observed results, not the original plan's expectations.

Write [a handoff](../templates/handoff.md) of at most 50 lines / 500 words. Check its timestamp,
full main SHA, required sections, and links. Record the stages still untested at representative
scale. Keep the handoff advisory and local; durable findings belong in tracked records or PRs.
Clear planner context only after these records are complete, then start the next takeoff.

## Failure and recovery

A stalled/crashed executor does not surrender ownership automatically. The supervisor establishes
whether it is still running; the planner records cancellation or redispatch and explicitly releases
resources before another executor proceeds. Preserve the original assignment identity and evidence;
revise the spec explicitly if scope changed. Lost local round state is reconstructed from PR metadata,
branches, checks, and durable item records. Never infer success from a missing process or green checks
for another revision.


For unattended execution, apply [the supervision contract](supervision.md). Resolve routine choices
under [standing decision authority](decision-policy.md); queue reserved questions and continue only
independent authorized work. A dependent assignment remains blocked until answered.

Runtime phase transitions and closure follow [SPEC.md](../SPEC.md). Structured manifests/results
carry machine state; Markdown explains evidence and reasoning. A new round starts only after the
previous round has a reconciliation record, including when work was cancelled or blocked.
