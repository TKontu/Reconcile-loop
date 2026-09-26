# Optional unattended supervision

The manual loop does not need a supervisor. An unattended implementation should preserve the same
[workflow](workflow.md) and add the lifecycle contract below. This is an implementation specification,
not bundled automation. Adapt [the supervisor configuration](../templates/supervisor.md) first.

## Session and process boundaries

Start a fresh planner session for each round. Within a round, resume its session across planning,
review, merge and reconciliation when supported. At the boundary, finish durable records, validate
the handoff, end the session, and start the next round without its conversation history. A new
process is insufficient if the runner automatically resumes an old session; explicitly create a
new session identity. Do not rely on an agent clearing its own context or relaunching itself.

Run the supervisor independently of the planner and executors. It may launch, wait, observe and
stop within granted authority; it must not invent scope, approve a decision, or weaken merge gates.

## Mechanical state and phase results

Persist round ID, pinned base, phase, session ID, assignment-to-runner mapping, PR/head identities,
policy revision, timestamps, logs, and explicit completion/failure reasons. Protect logs as potentially
sensitive and define retention. Keep durable acceptance and decisions in canonical project records.

Every phase must return a structured status and its expected artifacts. Check process exit status,
runner-reported error status, and the artifacts together. A successful process exit or an agent's
idle/done state alone is not engineering success. API failures mean unknown state, never an empty
successful result. Use an explicit round ID returned by planning rather than guessing by directory
modification time. Use structured manifests and PR APIs, not terminal scrollback, for control flow.

## Dispatch and completion

Preflight every target before sending any packet: matching base and digest, valid ownership,
provisioned artifacts, available resources, and an idle registered runner. Map assignments explicitly
to runners; do not assume assignment numbering or array positions define ownership.

Dispatch independent assignments, then wait under bounded deadlines. Record each acknowledged send
so a partial dispatch can be recovered without duplicating active work. Require the expected PR,
matching metadata, and required checks; a missing PR is a finding. For merge completion, verify each
expected PR's actual merged state and revision. No open PRs does not prove success: a PR can be
closed without merging, absent, or invisible due to a failed query.

## Limits and durable halt

Configure phase timeouts, executor deadlines, maximum rounds, model-turn/cost budgets where supported,
and a consecutive-no-progress limit. Main revision advancement is a useful liveness signal, not a
measure of product progress: also record accepted outcomes and remaining frontier blockers.

Persist a halt record containing time, round, phase, reason, relevant logs, active workers/resources,
and required recovery action. Halt on failed/timed-out phases, ambiguous dispatch, missing results,
unsatisfied merge gates, invalid handoff, or repeated no-progress rounds. Distinguish an exhausted
backlog from work blocked on decisions. Never retry merely because there ought to be executable work.

A queued decision blocks only its dependent work; independent authorized work can continue. If no
such work exists, stop and surface the queue. Do not loop indefinitely or manufacture scope.

## Recovery and cancellation

On interruption, stop launching work and inspect surviving child processes. Do not release resources
while a worker may still use them. Record whether workers were stopped or left running. On restart,
inspect the prior round's manifests, Git/PR state, checks and processes before resuming a phase.

Never blindly replay a phase that may have mutated state. Retry only after proving it is safe or
idempotent. A single clarification reminder is reasonable for an agent blocked on a decision already
within its authority; it cannot override a reserved action or stand in for an answer.

Clear a halt explicitly after its cause is resolved; clearing the marker alone does not validate the
round. Resume existing work with its identity intact rather than automatically planning a new round.

## Authorization and runner adapters

Keep [decision authority](decision-policy.md) separate from runner configuration. An auto-run setting
cannot grant merge, deployment or destructive-operation authority. Preserve normal runner permission
checks. Pass the immutable packet unchanged, with a separately versioned policy reference/context.

An adapter implements start/resume, dispatch acknowledgement, structured status, wait, and cancellation
using the chosen runner's supported interfaces. Manual packet delivery remains a valid adapter.
Notifications, when authorized, announce state; they are not approval or the durable decision queue.
