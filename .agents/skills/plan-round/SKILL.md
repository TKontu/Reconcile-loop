---
name: plan-round
description: "Select executable work and prepare isolated assignments at one pinned base."
---

# plan-round

Use this skill when the user requests `plan-round`, `$plan-round`, or `/plan-round` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the plan-round procedure](../../../.agent/commands/plan-round.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
