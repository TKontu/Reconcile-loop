# review-round

Follow [the shared contract](common.md).

Input: explicit round ID.

Read the ledger and resolve PRs by recorded branch/identity. API failures or missing PRs are unknown
or incomplete, not accepted work. Verify each base/spec digest, assigned scope, owned records and
actual PR head. Use [pr-verdict](pr-verdict.md) or [review](review.md) according to configured review
policy; a prior review of another head is stale.

Require all owed gates for the reviewed head. Start deferred integration only with the configured
safe environment/trigger and authorization; do not assume a magic label exists. Record skips and
outstanding owners. Inspect sibling interactions and changes in main since the round base.

Record ready, awaiting executor fix, or blocked with evidence in the round ledger. Small corrections
are allowed only within the existing editing authority; after any change refresh affected review and
checks. Route design/scope changes to planning and supply a bounded fix request for larger defects.
Stop with per-PR readiness and decisions owed. No merging in this phase.

Only the coordinator records manifest transitions; keep reviews bound to current result attempt and
head. Follow [the protocol states](../../SPEC.md) and reject stale or mismatched identities.
