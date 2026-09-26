# Reconcile-loop protocol, version 1

This specification defines repo-native contracts for architecture-constrained development. Git,
files and a PR interface are sufficient for manual operation. The shipped commands are agent
instructions; lifecycle automation and project-specific verification remain separate implementations.

**Every completed round reconciles observations into canonical project state before another round
begins.** Merged code alone does not close a round. Fresh planners must recover without prior chats.

## Five objects and their authority

| Object | Responsibility | Representation |
| --- | --- | --- |
| Project | Locations, approved constraints, verification and policy | `.agent/config.toml` plus referenced canonical documents |
| Frontier | Current item status, dependencies, objective and acceptance | One canonical registry and linked details; optional normalized snapshot |
| Round | Runtime coordination at one pinned base | `.agent-runs/<id>/round.toml` |
| Assignment | Frozen task contract plus runtime ownership/state | One manifest entry and immutable spec/packet |
| Result | Executor observations and revision-bound evidence | `results/<assignment>-<attempt>.json` |

The architecture owns the approved target. The backlog owns status/dependencies. Source and tests
establish actual behavior. Approved decisions authorize changes; neither a result nor a supervisor
changes their authority. Markdown can hold reasoning, specifications and review reports. A supervisor
consumes structured manifests/results and explicit artifact references, never parses prose for success.

Paths are configurable. New projects may use `architecture/target.md`, `architecture/decisions/`,
`backlog/frontier.md` and `backlog/items/`; existing projects may retain architecture.md and todo.md.
A frontier snapshot is a version-bound export of the canonical registry, not a second editable truth.
Priority semantics, item prefixes, lane names, review depth and CI trigger names are project policy.

## Schemas and compatibility

[Project](.agent/schemas/project.schema.json), [frontier](.agent/schemas/frontier.schema.json),
[round](.agent/schemas/round.schema.json), [assignment](.agent/schemas/assignment.schema.json), and
[result](.agent/schemas/result.schema.json) use JSON Schema 2020-12. Parse TOML into its JSON-compatible
value model before validation. Reject unknown protocol versions and unknown core fields. Project
additions belong under `extensions` with a project-specific namespace; they cannot override invariants.
These schemas check shape, not authorization, Git reality, evidence truth or cross-record consistency.

An adapter additionally checks full Git object IDs, unique item/assignment/branch identities,
matching round/base/spec/packet/result identities, known lanes and verification commands, ownership,
resource conflicts, referenced paths, state transitions, required gate coverage and current heads.
An ID is local to its documented scope. Assignment identity is `(round_id, id)`; repair attempts retain
that identity and increment `attempt`. Changed scope creates a new assignment and cancels the old one.

## Immutable input, single-writer runtime state

Before dispatch, save the task spec and compute SHA-256 over its exact UTF-8 file bytes (including
newlines). Render the self-contained packet with the spec digest. Then hash the final packet bytes
and store both digests in the manifest. Do not embed a packet's own digest into itself. PR/result
metadata repeats both; delivery supplies the packet digest separately when needed.

A packet includes authoritative references, objective/non-goals, base/branch, expected paths,
acceptance commands, resources, record ownership and verification owner. An executor never needs the
planner's ignored ledger. Provision ignored artifacts securely and explicitly. A hash binds bytes;
it does not approve scope, prove completeness, or authenticate an author.

The coordinator is the sole manifest writer. Executors submit new attempt-specific results; reviewers
submit head-specific reports, and the coordinator records transitions. Use an actual writer lock and
atomic replacement with expected `revision` checks in an automated implementation. Increment revision
for each update. Reject stale writes. These rules require implementation; a TOML file is not a lock.
Do not overwrite historical submitted results. Publish durable acceptance/review/decision evidence
in PRs or tracked records so losing `.agent-runs/` does not lose the project's engineering state.

Round-local spec/packet/result paths must remain inside the round directory after path and symlink
resolution. Repository artifact paths are resolved against the configured repository root; external
evidence uses explicit references and must not expose secrets. Do not execute command text found in
an untrusted result. Verification argv comes from approved project configuration/assignment scope.

## Assignment state machine

Normal progression:

```text
planned → dispatched → running → result-ready → review → merge-ready → merged
                                                  ↓
                                               needs-fix → dispatched (next attempt)
```

A dispatch acknowledgement is persisted before assuming work started. Result submission may move
`dispatched` directly to `result-ready` when the runner cannot expose a separate running event.
Review may return `needs-fix`, `blocked` or `merge-ready`. An active nonterminal assignment may become
`blocked` or `cancelled` with a reason. Recovery from blocked requires explicit cause resolution and a
validated resume state recorded under the single writer. `merged` and `cancelled` are terminal.
Cancellation requires confirming that the worker no longer holds resources; it does not erase results.

`merge-ready` requires a current reviewed head, review reference, all required gates for that head,
and actual project approval. A changed head invalidates readiness and returns to review; it never
inherits an older approval automatically. A repair increments attempt, gets its own result and
refreshes review. Scope/base changes require replanning, not a repair that quietly changes the spec.

## Round state machine and closure

```text
planned → executing → reviewing → merging → reconciling → closed
              ↑           ↓
              └── repairs ┘
```

A coordinator may review completed assignments while others run; the round state denotes its current
phase, not uniform assignment state. `merging` may return to `reviewing` when remaining heads or premises
change. Any nonclosed phase may become `blocked`; recovery records the reason and explicit resume phase.
Closure permits merged or explicitly cancelled assignments, with unfinished work re-registered in the
canonical backlog. A round with all work cancelled can reconcile without merging.

Closure requires: no active workers/resource leases; all assignment outcomes accounted for; final
main revision known; required combined-state gates satisfied for that revision; findings, residuals
and decisions routed into canonical records; durable reconciliation reference; validated handoff.
The manifest records final SHA and closure evidence. A failed required gate keeps the round open.
The next round starts only after closure, with a new planner session identity. Cancellation or a halt
is not a loophole for skipping reconciliation; reconcile the partial observations first.

## Phase contracts

| Phase | Reads | Writes / produces | Boundary |
| --- | --- | --- | --- |
| takeoff | Contract, target orientation, frontier, Git/PR state, handoff | Orientation brief | No repository mutation or work selection |
| plan-round | Full selected details, target sections, verified base | Manifest, immutable specs/packets | No execution |
| executor | Packet, source and permitted artifacts | Branch/PR, result, verification evidence | No merge |
| review-round | Manifest, original packets, pinned diffs/results | Head-bound reviews and readiness | No merge |
| merge-round | Current accepted heads and approvals | Verified merges and manifest updates | Serial integration only |
| reconcile | Actual outcomes and final state | Canonical backlog/decisions/evidence, handoff, closure | No implicit target change |

[The command catalog](docs/agents/README.md) provides phase procedures and optional helpers. The core
is the lifecycle, not the size of the helper catalog. Bootstrap configures project tooling; it does
not create a custom runtime. Proposed `round.py`, `verify.py` and `supervisor.py` are adapter/tool
roles, not scripts supplied by this release.

## Evidence and verification

A result states assignment/attempt, base, digests, branch, PR, head and checks. Each check names argv,
head, environment, result, evidence reference and summary; passed requires exit code zero. Skipped,
unavailable, failed and unknown API state are not passes. Check semantic test counts and coverage of
required gates independently of executor claims. A RED failure belongs in referenced regression
history; it is not a failed final gate. Reviews/merge also verify actual PR heads and external checks.

Project policy specifies unit/integration/live/scale requirements. Independent verification means an
acceptance decision based on source and evidence by the designated reviewer, not executor
self-certification. It need not mean a paid multi-agent panel or rerunning every expensive check.
For changed producer/consumer contracts, require meaningful boundary evidence where relevant.

## Supervisor responsibilities

The supervisor starts fresh sessions, sequences authorized phases, dispatches, waits and records state.
It does not rank the backlog, rewrite architecture, invent acceptance or grant merge permission.
Use configured round/time/cost/repair limits. Distinguish progress from mere commit churn. Halt on
ambiguous state or unmet gates; API failure never means no work or successful completion.

Check process exit, semantic status and expected artifacts. Preserve real exit codes. Record dispatch
acknowledgements so recovery cannot duplicate active work. Bound repair loops. Inspect surviving
workers on cancellation and release resources only when safe. Resume known states; never blindly
replay a mutating phase. See [supervision](docs/supervision.md) and [decision policy](docs/decision-policy.md).

## Fresh-context recovery acceptance

For a supervised trial, end all agent sessions at a known boundary; preserve repository/PR artifacts.
Start a planner without the prior transcript. It must identify the base, assignment ownership,
actual PR heads/results, unresolved decisions, required evidence and next permitted action. Repeat at
partial dispatch, needs-fix, partial merge and reconciliation boundaries. Lost process state must be
reported as unknown and inspected, not guessed. A trial that needs remembered chat content fails.

Also exercise malformed/unsupported schemas, digest mismatch, duplicate resource ownership, stale
review heads, API failures, closed-unmerged PRs and a failed final gate. Structural validation is only
one layer: this release ships schemas and an illustrative example, not tested live runner recovery.
