# commit-push-pr

Follow [the shared contract](common.md).

Input: assigned change and authorization to commit/push/open a PR, supplied by user or task contract.

Inspect current branch, remote, diff and staged set. Never publish unrelated staged changes. Stage only
owned intended paths when authorized; if attribution is ambiguous, resolve it before committing.
Review the concrete diff, run [secrets-check](secrets-check.md) and [verify](verify.md), then prepare
[the PR evidence](../../templates/pull-request.md) with base/spec identity and actual gate results.

Commit with the project's convention, push the task branch without force, and create or update the
corresponding PR. Use structured tool fields or a body file for multiline text. Do not push directly
to the default branch or merge. Check PR identity/head and monitor required executor checks within a
bounded deadline using [ci-watch](ci-watch.md). Missing credentials/network capability is a concrete
blocker, not permission to use another account or bypass controls.

If publication is not yet authorized, finish the diff, checks and proposed PR text first; present the
specific action for approval. Do not ask again when it is already authorized. Report PR URL, revision,
results and pending verification/decisions. Do not claim deferred gates ran.
