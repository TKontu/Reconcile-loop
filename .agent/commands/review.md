# review

Follow [the shared contract](common.md).

Input: staged/working diff, explicit revision range, or PR. State which revision/scope was inspected.

Read metadata and changed paths first, then assignment references and relevant source. Check actual
behavior, edge cases, security boundaries, concurrency, compatibility, test relevance, and unrequested
changes. Verify callers, producers/consumers, default behavior, and any deferred wiring claim. For
large collections inspect query limits, memory, transaction duration and checkpoints. Check new
flags/fallbacks for owners and lifecycle gates and tactical debt for a named successor.

Use [the review record](../../templates/review.md). Each finding needs a location, concrete
failure scenario, evidence and severity; distinguish confirmed defects from untested concerns.
State residual risks and missing verification even when no defects are found. Do not infer a pass
from unrun checks. No edits, pushes, comments or merges unless separately requested.
