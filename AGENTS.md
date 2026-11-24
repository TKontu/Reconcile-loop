# Reconcile-loop contributor contract

This repository maintains the lean workflow, phase instructions, templates and local round CLI.
Read README.md and SPEC.md. Keep one maintained version; expanded features remain in the archived
`docs/standalone-patterns` branch until a demonstrated need justifies adding them here.

- `.agent/commands/` owns phase procedures and optional helpers (`status`, `pr-verdict`,
  `loop-manager`); runner
  wrappers and `.claude/agents/` subagents point there or stay runner-specific. Avoid duplicate policy.
- Preserve the protocol's isolation, evidence and reconciliation guarantees. Keep project-specific
  rules and generic development helpers out of the lean core. Unattended supervision lives only in
  the optional `scripts/round_supervisor.py`, `scripts/lanes.py` and `.agent/supervisor.md`; no
  phase, template or `round.py` behavior may depend on them.
- For CLI behavior changes demonstrate a failing test first, implement the smallest fix, then run
  `python3 -m unittest discover -s tests`. Run `git diff --check` and inspect links before publishing.
- Review staged changes for secrets and private source material. Preserve unrelated work; never
  force-push. Do not claim local metadata checks prove external review, CI, or merge correctness.

For adopting projects, merge templates/AGENTS.md into their own instructions. This contributor file
is not a replacement for an application's operating contract.
