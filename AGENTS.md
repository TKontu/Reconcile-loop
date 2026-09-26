# Reconcile-loop contributor contract

This repository contains a vendor-neutral development pattern, documentation, and templates.
It is not an agent runner or a copy of an application's architecture or backlog.

- Read README.md, then docs/workflow.md and the relevant template before editing.
- Keep the existing conceptual overview intact; put operational detail in linked guides.
- Keep examples fictional and portable. Do not copy credentials, private data, infrastructure
  addresses, product backlogs, or project-specific decision IDs into this repository.
- Keep one definition of each rule; templates link to guides rather than inventing new policy.
- Clearly distinguish manual conventions from implemented enforcement. There is no bundled CLI,
  supervisor, lease service or CI workflow. Skill/command entry points are instruction wrappers.
- SPEC.md owns the protocol; `.agent/commands/` owns phase procedures; `.agent/schemas/` owns
  structural contracts. Keep wrappers thin and verify examples against the schemas.
- Preserve unrelated changes. Use a separate branch for contributions; never force-push.
- For documentation changes, check relative links, template consistency, and git diff --check.
  For future executable tooling, demonstrate a failing behavior test before implementing it and
  run targeted tests. Do not claim checks or automation that have not actually run.
- Review the diff for secrets and identifiable private source material before publishing.

The adoption contract in templates/AGENTS.md is for consuming projects, not this pattern library.
