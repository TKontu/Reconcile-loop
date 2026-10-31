---
name: merge-round
description: "Merge independently reviewed work under the project policy and record actual outcomes."
---

# merge-round

Use this skill when the user requests `merge-round`, `$merge-round`, or `/merge-round` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the merge-round procedure](../../../.agent/commands/merge-round.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
