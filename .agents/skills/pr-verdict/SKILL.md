---
name: pr-verdict
description: "Run a risk-tiered, head-bound review panel on one PR; advisory only."
---

# pr-verdict

Use this skill when the user requests `pr-verdict`, `$pr-verdict`, or `/pr-verdict` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the pr-verdict procedure](../../../.agent/commands/pr-verdict.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
