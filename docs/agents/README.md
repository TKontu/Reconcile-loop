# Agent command and skill pack

Each operation has one canonical procedure in `.agent/commands/`, a discoverable
`.agents/skills/<name>/SKILL.md` entry point, and a `.claude/commands/<name>.md` slash-command
entry point. The wrappers share the same procedure; there are no separately maintained workflow
copies. Other runners can read the canonical procedure and shared contract as a plain prompt.

## Install and start

Copy or merge `.agents/skills/`, `.claude/commands/`, `.agent/`, `docs/agents/`, the root workflow guides
in `docs/`, and `templates/` into the target repository, preserving relative paths and existing files. Include `SPEC.md` for the protocol contract.
Do not copy this library's root contributor AGENTS.md over the target's instructions. Use the
[bootstrap procedure](../../.agent/commands/bootstrap.md) to merge the adoption contract, map existing architecture,
README and TODO files, configure verification and create `.agent/config.toml` from
[the configuration template](../../templates/config.toml), with project policy from
[the policy checklist](../../templates/project.md). Never execute unresolved command placeholders.

In a runner that discovers the supplied slash commands, start with `/bootstrap` and then `/takeoff`.
In a skill-capable runner, invoke the corresponding skill by name using that runner's interface.
If discovery is unavailable, ask the agent to read the canonical procedure directly. No particular
vendor CLI, model, service or package manager is required for manual operation.

Typical manual round:

```text
bootstrap (once per adoption)
takeoff → plan-round → dispatch-round → execute-task
        → review-round → merge-round → reconcile → handoff → fresh planner
```

`reconcile` includes handoff; a separate `handoff` invocation refreshes the same bounded delta when
needed, rather than requiring a duplicate step. `orchestrate` coordinates one authorized round.
`supervise` requires an existing tested lifecycle adapter for repeated unattended rounds; these
instructions do not create a daemon, install dependencies or bypass permissions.

## Core and optional operations

The five planner phase commands are `takeoff`, `plan-round`, `review-round`, `merge-round`, and
`reconcile`. `execute-task` defines the executor side of that protocol. `bootstrap`, assignment,
dispatch and handoff helpers make adoption and delivery practical. Review lenses, CI monitoring,
framework helpers and unattended supervision are optional; projects need not invoke every helper.
The five core commands may also be used as plain prompts without installing either vendor wrapper.

## Operations

| Name | Purpose |
| --- | --- |
| [bootstrap](../../.agent/commands/bootstrap.md) | Adapt the reconcile-loop workflow to a new or existing project without overwriting its architecture, README, or backlog. |
| [takeoff](../../.agent/commands/takeoff.md) | Orient a fresh planner from durable project state and produce a takeoff brief without selecting work. |
| [status](../../.agent/commands/status.md) | Report current backlog, PR, decision, and verification status without changing project state. |
| [plan-round](../../.agent/commands/plan-round.md) | Select a bounded executable batch and create immutable assignments at one verified base revision. |
| [assign-agent](../../.agent/commands/assign-agent.md) | Prepare one self-contained executor assignment with pinned scope, ownership, resources, and acceptance. |
| [dispatch-round](../../.agent/commands/dispatch-round.md) | Preflight and dispatch a planned round to isolated executors, or provide manual packet delivery. |
| [execute-task](../../.agent/commands/execute-task.md) | Carry a bounded assignment through implementation, verification, and its authorized PR handoff. |
| [review](../../.agent/commands/review.md) | Review the current diff against assigned scope and source behavior before publication; do not edit or merge. |
| [pr-verdict](../../.agent/commands/pr-verdict.md) | Produce an evidence-based PR verdict using risk-scaled review lenses tied to the exact head revision. |
| [review-lens](../../.agent/commands/review-lens.md) | Apply one focused read-only review lens to pinned PR artifacts, with concrete evidence and limits. |
| [review-round](../../.agent/commands/review-round.md) | Review every result in a named round against its frozen assignment and required exact-head evidence. |
| [merge-round](../../.agent/commands/merge-round.md) | Serially merge reviewed round results under the project merge policy and recheck remaining work. |
| [reconcile](../../.agent/commands/reconcile.md) | Update canonical project state from observed round outcomes, verification results, and remaining decisions. |
| [handoff](../../.agent/commands/handoff.md) | Write and validate a bounded advisory session delta for the next fresh planner. |
| [orchestrate](../../.agent/commands/orchestrate.md) | Coordinate one authorized development round from takeoff through reconciliation, preserving role boundaries. |
| [decisions](../../.agent/commands/decisions.md) | List, queue, or apply durable operator decisions while keeping dependent work explicitly blocked. |
| [resume-round](../../.agent/commands/resume-round.md) | Recover a halted or partially dispatched round from observed state without blindly replaying mutations. |
| [supervise](../../.agent/commands/supervise.md) | Monitor or drive explicitly authorized bounded rounds using an existing tested runner adapter. |
| [debug](../../.agent/commands/debug.md) | Investigate a reproducible fault and identify its cause before applying a scoped fix. |
| [tdd](../../.agent/commands/tdd.md) | Implement an assigned behavior change through an observed failing regression test and targeted verification. |
| [test](../../.agent/commands/test.md) | Run the project-configured targeted test selection and report failures, skips, and environment accurately. |
| [lint-fix](../../.agent/commands/lint-fix.md) | Apply the configured formatter and safe lint fixes to assigned files, then inspect and verify the result. |
| [verify](../../.agent/commands/verify.md) | Run required completion checks on the actual candidate revision and report evidence before claiming success. |
| [secrets-check](../../.agent/commands/secrets-check.md) | Inspect the proposed publication set for secrets and private source material without disclosing values. |
| [commit-push-pr](../../.agent/commands/commit-push-pr.md) | Publish an authorized scoped change as a commit and PR with assignment and verification evidence. |
| [update-todos](../../.agent/commands/update-todos.md) | Update only permitted canonical backlog records using observed acceptance evidence. |
| [pipeline-review](../../.agent/commands/pipeline-review.md) | Trace a specified production entry point through its consumers, state changes, and outputs. |
| [new-endpoint](../../.agent/commands/new-endpoint.md) | Implement an assigned API endpoint using the adopting project’s existing framework and contracts. |
| [quick-fix](../../.agent/commands/quick-fix.md) | Apply a specified mechanical correction on an existing task branch without expanding behavior or scope. |
| [ci-watch](../../.agent/commands/ci-watch.md) | Monitor required PR checks for a pinned head with a bounded wait and report actual outcomes. |

## What was adapted

The lifecycle commands, assignment/orchestration skills, development checks and PR helpers from the
source project are represented here. Its three specialized agent roles become `quick-fix`,
`review-lens` and `ci-watch`, usable without vendor-specific model names. The outer driver's dispatch,
status, queued decisions, bounded supervision and recovery are covered by their matching procedures.

`new-endpoint` and `pipeline-review` are optional, stack-neutral helpers. GitNexus-specific skills
are not bundled: they depend on an external tool and are not part of the reconcile loop. Install
such tools separately if useful; verify their navigation claims against source. Application-specific
validators, database guards and round-management scripts must be supplied by the adopting project
or replaced by the explicit manual checks in these procedures. No procedure calls those absent tools.
