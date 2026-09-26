# Extraction notes

This pattern library was developed from the Iknos repository's operational conventions and the
existing Reconcile-loop README. The extraction emphasizes the stable process rather than application
architecture. Source conventions inspected on 2026-09-26 included:

- AGENTS.md: authority, isolated execution, evidence and data safety.
- docs/agents/workflow.md and parallel-rounds.md: round lifecycle and resource ownership.
- docs/agents/task-prompt.md: self-contained packets, digest binding, connections and scale.
- The takeoff, plan-round, review-round, merge-round, reconcile and handoff command documents.
- docs/todo.md's execution contract and architecture engineering principles.

The original Reconcile-loop README remains the conceptual introduction. New guides generalize
project-specific service names, commands, decision IDs, model choices and approval exceptions.
Application source, backlog items, private inputs, credentials and infrastructure are not included.

The source project has tooling for parts of this process. That tooling was not copied: these files
provide documented contracts and manual templates, not an implementation or a claim that every
safety check is automatically enforced. Adoption requires project-specific commands and policies.


A second extraction inspected the local `iknos-loop` driver on 2026-09-26: its README,
standing decision policy, and lifecycle, dispatch, status, decision-queue and reminder scripts.
The resulting supervision and decision-authority guides retain fresh-session boundaries, bounded
execution, explicit recovery and asynchronous decisions. They do not copy the shell implementation,
runner dependencies, project-specific exceptions, or assumptions that every blocker is avoidable.
Source documentation and implementation differed in places, so the generalized contracts specify
observable outcomes rather than treating that driver as a validated reference implementation.

The packaged procedures also adapt the source project's development helpers and three review/fix/CI
roles. Their bodies live once under `.agent/commands/`; skill and slash-command wrappers point there.
The versioned protocol, five structural schemas and fictional worked example incorporate the proposed
repo-native layout. Project taxonomy and tool names remain configurable. No runtime scripts were copied.
