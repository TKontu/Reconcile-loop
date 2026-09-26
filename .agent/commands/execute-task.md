# execute-task

Follow [the shared contract](common.md).

Input: complete immutable assignment packet.

Verify project contract/profile, packet identity, scope and provided base before creating the branch
in a clean isolated workspace. Compare the pinned base with fetched default branch; return drift to
planning. Read the complete item detail and named architecture sections. Confirm artifacts, service
access and required gates are provisioned. Inspect source callers and producer/consumer boundaries.

For behavior changes follow [tdd](tdd.md); for faults use [debug](debug.md). Implement only assigned
scope. Docs-only work uses relevant structural/consistency checks. Record actual evidence and scale
limits. Follow [verify](verify.md), [review](review.md), and [secrets-check](secrets-check.md) before
[commit-push-pr](commit-push-pr.md) when publication is authorized by the assignment/user.

Update only named records when permitted. An implementation PR does not make an unmerged item done
under a merge-based acceptance contract. Return scope conflicts and reserved decisions to planning;
continue only independent authorized work. Stop at the PR and required executor checks, or report
specific unavailable gates and their owner. Never self-merge or silently waive acceptance.

Return attempt-specific structured result metadata matching [the result schema](../schemas/result.schema.json),
including actual head, environment, command and evidence. Submit it to the coordinator; do not edit
the planner manifest. Put durable evidence in the PR even if the local result is lost.
