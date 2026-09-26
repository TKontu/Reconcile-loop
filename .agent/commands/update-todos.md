# update-todos

Follow [the shared contract](common.md).

Input: item IDs, actual results and the caller's ownership (executor or planner).

Read the sole registry and complete details from the profile. Verify the relevant PR/measurement and
acceptance before editing. Executors change only named rows/details permitted by their assignment;
planner-owned frontier text, priorities, new IDs and cross-item dependencies remain planner work.

Keep status single-valued. Record links, as-of revision, actual outcome and residuals; do not mark
acceptance complete merely because code exists or a PR is open. New unassigned work is a proposed
follow-up to planning, not an implicit scope extension. Target changes follow the decision process.
Validate references/schema with configured tools or direct inspection, and report precisely which
records changed. Use [reconcile](reconcile.md) for a whole round's frontier update.
