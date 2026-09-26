> **Experimental archive:** this branch preserves the expanded pattern pack for reference.
> It is not a supported edition. The maintained lean workflow lives on `main`.

# Architecture-Constrained Agent Orchestration

A lightweight pattern for autonomous multi-agent engineering.

> **Agents are disposable. Project state is durable.**

The system works in short rounds instead of relying on one long-lived agent or a fully preplanned project.

```text
target architecture
      ↓
current frontier
      ↓
plan round
      ↓
execute
      ↓
review
      ↓
merge
      ↓
reconcile
      ↓
update backlog
      ↓
fresh planner
      ↓
repeat
```

## Core idea

The repository is the source of truth.

Durable state lives in:

- architecture and design constraints
- backlog and dependencies
- assignment contracts
- branches and pull requests
- tests and execution evidence
- bounded handoff state

Agent conversations are not project memory.

A fresh planner should be able to reconstruct the current state without access to previous sessions.

## Workflow

A round typically follows:

```text
/takeoff
/plan-round
agent execution
/review-round
/merge-round
/reconcile
```

### `/takeoff`

Starts a fresh planning session and reconstructs current state from the repository, backlog, PRs, and handoff.

### `/plan-round`

Selects the next executable and parallel-safe work and creates bounded assignments.

Each assignment defines:

- objective
- scope and non-goals
- authoritative references
- base revision
- acceptance criteria
- required validation

### Execution

Executors work independently in isolated branches, worktrees, containers, or other environments.

They return durable results such as:

```text
code
tests
measurements
PRs
```

### `/review-round`

Checks the implementation against the assignment, architecture, tests, and acceptance criteria.

### `/merge-round`

Integrates accepted work.

### `/reconcile`

Updates project state based on what actually happened.

Reconciliation may:

- close completed work
- expose blocked dependencies
- create new implementation tasks
- create investigations
- record failed experiments
- surface architecture decisions for human approval

This means the project does **not** need to be planned end-to-end.

Only the current frontier needs to be sufficiently specified.

## Fresh sessions

After reconciliation, the planner session is discarded.

The next planner starts from durable project state:

```text
Git
architecture
backlog
PR state
handoff
```

This reduces stale assumptions and prevents conversation history from becoming an undocumented dependency.

## Separation of responsibilities

```text
Supervisor
  manages lifecycle and waits for completion

Planner
  decides what should happen next

Executors
  perform bounded work
```

The supervisor should remain simple. It manages liveness, not engineering judgment.

A typical loop is:

```text
start planner
→ /takeoff
→ /plan-round
→ dispatch executors
→ wait
→ /review-round
→ /merge-round
→ /reconcile
→ stop planner
→ start fresh planner
```

## Why it generalizes

The pattern works for any project where:

- the target architecture or desired state is explicit
- work can be expressed as bounded increments
- completion can be verified
- results can be reconciled back into durable project state

The specific runner does not matter. Executors may be Claude Code, Codex, OpenCode, humans, CI jobs, or specialized tools.

The central abstraction is:

> **A controlled transition from one verified project state to the next.**


## Use this repository

Start with the [adoption guide](docs/adoption.md), then follow the
[round workflow](docs/workflow.md). The [pattern catalog](docs/patterns.md) explains the invariants
and the [extraction notes](docs/provenance.md) describe their origin and scope.

Copy and adapt the [project contract](templates/AGENTS.md),
[architecture](templates/architecture.md), [backlog](templates/todo.md), and
[item detail](templates/item.md). For each round use the [assignment](templates/assignment.md),
[round record](templates/round.md), [PR evidence](templates/pull-request.md),
[review](templates/review.md), [reconciliation](templates/reconcile.md), and
[handoff](templates/handoff.md) templates.

The [versioned protocol](SPEC.md) defines the stage contracts. The
[command catalog](docs/agents/README.md) includes 30 reusable procedures with skill and slash-command
entry points. Begin with `bootstrap` to adapt the pack to your project. The
[worked example](examples/session-service/README.md) shows structured round and result artifacts.
The pack provides agent instructions and schemas; an unattended supervisor is not implemented.


For unattended operation, also adopt the [supervision contract](docs/supervision.md) and
[standing decision policy](docs/decision-policy.md). These cover fresh sessions, dispatch,
halt/recovery, and queued decisions; runner implementations remain project-specific.
