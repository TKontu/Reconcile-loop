---
name: review-round
description: "Review candidate heads against their original assignments and actual evidence."
---

# review-round

Use this skill when the user requests `review-round`, `$review-round`, or `/review-round` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the review-round procedure](../../../.agent/commands/review-round.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
