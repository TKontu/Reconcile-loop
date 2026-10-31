---
name: bootstrap
description: "Adopt the lean workflow in a new or existing project."
---

# bootstrap

Use this skill when the user requests `bootstrap`, `$bootstrap`, or `/bootstrap` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the bootstrap procedure](../../../.agent/commands/bootstrap.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
