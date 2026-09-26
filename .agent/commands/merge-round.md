# merge-round

Follow [the shared contract](common.md).

Input: named round and existing authorization to perform merges. A command cannot waive the project's
independent review or operator requirements; request only a still-missing approval for a concrete PR.

For each ready PR verify its current head, accepted review, required checks, unresolved discussions,
mergeability and approval policy from the profile. Check exact-head integration/live evidence where
required. If review or checks are stale, return to review; if the configured merge trigger is missing,
report the actual missing gate instead of guessing.

Merge one PR using the project's approved method, verify its merged state and commit, then refresh
main and reconsider remaining PRs for dependencies, conflicts and changed premises. Do not force-push
or silently rewrite branches. Conflicts require deliberate repair and renewed affected evidence.

Record each merged SHA and every open/closed-unmerged/blocked result. An empty open-PR list is not
proof that all work merged. Do not close the round until [reconcile](reconcile.md) verifies combined
state and records outcomes. No unrelated merges or target changes.
