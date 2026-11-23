---
name: loop-manager
description: "Watch the optional round supervisor: brief the operator, check its output, pass rulings; read-only towards round work."
---

# loop-manager

Use this skill when the user requests `loop-manager`, `$loop-manager`, or `/loop-manager` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the loop-manager procedure](../../../.agent/commands/loop-manager.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
The supervisor it watches starts Claude Code sessions; this helper only observes and relays.
