# Project agent contract

Adapt all placeholders before adoption. This file is the canonical cross-runner contract.

- Approved target: `<architecture path>`; sole status registry: `<backlog path>`; complete details:
  `<item path convention>`; decisions: `<decision path>`. Source establishes actual behavior.
- Read the assigned row, complete detail, and named architecture sections. Handoffs are advisory.
- Planner owns assignment, cross-item state, new IDs, resources, and merge order. Executors must
  return missing decisions instead of expanding scope or changing the target.
- Execute in a separate clean worktree/clone at the pinned base. Preserve unrelated work; never
  force-push. Edit only assigned records. Check callers and data-shape consumers in source.
- Use test-first development for behavior changes and surgical checks during development.
- Local gate: `<command>`; integration gate/environment: `<command and disposable target>`;
  live gate: `<command or not applicable>`; skip reporting: `<policy>`.
- Resource policy/runbook: `<path>`; persistent reset approval: `<authority and safeguards>`.
- Before PR: review diff, check secrets/private data, run required checks, and record exact evidence.
- Merge authority: `<reviewer/operator>`; independent review policy: `<policy>`.
- After merges, verify combined state and reconcile status, findings, residuals, and next frontier.
- Handoff is a bounded delta, at most 50 lines / 500 words; fresh planners reconstruct durable state.

- Workflow routing: `.agent/config.toml`; phase contracts: `.agent/commands/`; protocol: `SPEC.md`.
  These map the project's actual paths and commands; do not execute unresolved template placeholders.
