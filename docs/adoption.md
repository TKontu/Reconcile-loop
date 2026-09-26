# Adopt the pattern

Start with one planner, one executor, and one small verifiable outcome. Parallel execution is
optional. The loop can be run by humans using Git and a PR host; no particular agent vendor,
framework, language, database, or paid service is required.

## Bootstrap a consuming repository

Run [bootstrap](../.agent/commands/bootstrap.md) to perform the setup below with an agent.

1. Write the approved target using [the architecture template](../templates/architecture.md).
   State system boundaries, invariants, non-goals, and approval authority.
2. Create a single status registry from [the backlog template](../templates/todo.md) and put
   complete acceptance details in [item records](../templates/item.md). Specify only the current
   executable frontier; later work may remain proposed.
3. Adapt [the agent contract](../templates/AGENTS.md) into the project's root AGENTS.md. Point
   vendor-specific instruction files to it instead of maintaining copies.
4. Choose concrete local, integration, and live checks. Record their commands, environment,
   ownership, skip policy, and merge requirements. Document disposable versus persistent data
   resources and reset safeguards before permitting service access.
5. Run [takeoff through reconciliation](workflow.md) using [an assignment](../templates/assignment.md),
   [a PR evidence record](../templates/pull-request.md), and [a review](../templates/review.md).
6. Write [a bounded handoff](../templates/handoff.md), clear the planner context, and verify that
   the next planner can reconstruct state from the repository and PRs alone.

Suggested destination layout (paths are conventions you may adapt):

```text
AGENTS.md
README.md                      stable purpose and navigation
docs/architecture.md           approved target
docs/todo.md                   sole status/dependency registry
docs/items/                    complete item scope and acceptance
docs/decisions.md              approved decisions and deviations
docs/reconcile-log.md          dated round outcomes and measurements
.agent/config.toml             paths, verification and policy configuration
.agent/commands/                canonical phase procedures
.agent/schemas/                 versioned runtime contracts
docs/agents/                   command catalog and project policy
.agent-runs/                   ignored local packets and round ledger
HANDOFF.md                     ignored, advisory session delta
```

Keep durable acceptance evidence in
PRs or tracked reports, not solely in ignored local files. Provision any required ignored data or
configuration into executor workspaces explicitly; never paste secrets into an assignment.

## Start manually; automate proven repetition

The [command pack](agents/README.md) supplies canonical procedures in `.agent/commands/`,
skills in `.agents/skills/`, and slash-command wrappers in `.claude/commands/`. Start with
`bootstrap` to map your existing files into `.agent/config.toml` and establish project policy.
An unattended lifecycle adapter remains separate from these agent instructions.

A [round manifest](../templates/round.toml) is the central runtime record. The
[Markdown review view](../templates/round.md) is advisory, never a second state store.
A local ledger speeds coordination but is not the sole durable result store. Resource reservations
in that ledger are declarations, not locks: use a supervisor or actual locking if concurrent
processes need enforcement.

Projects choose check commands, branch protection, merge authority, resource names, review depth,
and model budgets. Keep those local choices distinct from the invariants in [the pattern](patterns.md).


## Before unattended operation

Adopt [decision authority](decision-policy.md), the [decision record](../templates/decision.md),
and [supervision](supervision.md). Fill in [the supervisor contract](../templates/supervisor.md)
and validate an adapter in a supervised round before allowing repeated autonomous rounds.
The manual workflow is self-contained; unattended execution additionally needs an implemented,
tested runner adapter and project-specific check/resource configuration.

For a new layout, `architecture/target.md` and `backlog/frontier.md` work as well as the
paths above. Configure them; do not rename an established project to satisfy the template.
See [SPEC.md](../SPEC.md) for the five objects, transitions and fresh-session recovery requirement.
