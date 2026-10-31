---
name: takeoff
description: "Orient a fresh planner from repository state without selecting work."
---

# takeoff

Use this skill when the user requests `takeoff`, `$takeoff`, or `/takeoff` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the takeoff procedure](../../../.agent/commands/takeoff.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
