---
name: handoff
description: "Write a small advisory delta that allows a fresh planner to reconstruct the next action."
---

# handoff

Use this skill when the user requests `handoff`, `$handoff`, or `/handoff` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the handoff procedure](../../../.agent/commands/handoff.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
