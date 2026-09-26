# status

Follow [the shared contract](common.md).

Input: optional item or round identifier.

Read the canonical registry/profile and relevant item records; inspect Git/PR/check state read-only.
Tally statuses from the registry's actual schema, then verify the tally. Separate ready work from
blocked/proposed work and name unmet dependencies and pending decisions. Link recent accepted
outcomes and current verification/scale residuals. Distinguish implementation maturity from measured
operating capability; a done item only proves its stated acceptance.

Report evidence as of a timestamp/revision. Treat unavailable APIs as unknown, not no open PRs or
all checks passed. Surface premise changes for reconciliation without editing the target, assigning
work, or changing records. No automatic retries, publication, or service access.
