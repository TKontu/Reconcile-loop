# Reconcile-loop contributor contract

This repository maintains the lean workflow, phase instructions, templates and local round CLI.
Read README.md and SPEC.md. Keep one maintained version; expanded features remain in the archived
`docs/standalone-patterns` branch until a demonstrated need justifies adding them here.

- `.agent/commands/` owns phase procedures; runner wrappers point there. Avoid duplicate policy.
- Preserve the protocol's isolation, evidence and reconciliation guarantees. Keep project-specific
  rules, generic development helpers and unattended supervision out of the lean core.
- For CLI behavior changes demonstrate a failing test first, implement the smallest fix, then run
  `python3 -m unittest discover -s tests`. Run `git diff --check` and inspect links before publishing.
- Review staged changes for secrets and private source material. Preserve unrelated work; never
  force-push. Do not claim local metadata checks prove external review, CI, or merge correctness.

For adopting projects, merge templates/AGENTS.md into their own instructions. This contributor file
is not a replacement for an application's operating contract.
