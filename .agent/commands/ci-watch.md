# ci-watch

Follow [the shared contract](common.md).

Input: repository/PR, exact head SHA, required checks and deadline.

Read-only: query structured PR/check state without editing files, commenting, triggering workflows,
pushing or merging. Distinguish queued, running, passed, failed, cancelled, skipped, missing and unknown
states. The required check list comes from the project profile/branch policy, not merely whatever
checks happened to appear. If the head moves, report stale observation instead of certifying it.

Poll at a reasonable bounded interval until required checks settle or the deadline arrives. For
failures return the smallest useful redacted diagnostic. Report SHA, each required check's result,
mergeability when available and remaining gates. API errors are unknown, not success. Do not silently
rerun failing workflows, and do not interpret a skipped required tier as a passing one.
