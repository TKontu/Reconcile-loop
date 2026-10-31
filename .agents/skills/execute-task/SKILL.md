---
name: execute-task
description: "Implement a bounded assignment and return revision-bound results without merging."
---

# execute-task

Use this skill when the user requests `execute-task`, `$execute-task`, or `/execute-task` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the execute-task procedure](../../../.agent/commands/execute-task.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
