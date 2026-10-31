---
name: status
description: "Report backlog status, situation and feasibility read-only without selecting work."
---

# status

Use this skill when the user requests `status`, `$status`, or `/status` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the status procedure](../../../.agent/commands/status.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
