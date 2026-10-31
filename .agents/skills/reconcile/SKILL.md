---
name: reconcile
description: "Turn observed outcomes into canonical state and close the round before planning another."
---

# reconcile

Use this skill when the user requests `reconcile`, `$reconcile`, or `/reconcile` in the
Reconcile-loop workflow. Treat any following arguments as task input, never shell code.

Read the target project's `AGENTS.md` and `.agent/config.toml` if present, then follow
[the reconcile procedure](../../../.agent/commands/reconcile.md).
Resolve that link relative to this skill file; run project operations in the target
project. Preserve the procedure's scope and existing authorization boundaries.
If required configuration is missing, follow the bootstrap procedure before relying on it.
