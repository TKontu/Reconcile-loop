# Lean protocol

## Authority and roles

The project config points to its approved architecture, one canonical backlog, verification command
and local merge policy. Linked item details carry complete acceptance. Source and checks establish
actual behavior; neither a handoff nor a conversation replaces these records.

The planner selects work, assigns ownership, reviews outcomes and updates cross-item state. Executors
work in isolated checkouts and return evidence. The designated reviewer/operator authorizes integration.
An agent's ready verdict is not merge permission. Routine choices within authorized scope proceed;
target changes and reserved actions follow project policy.

## One round, three records

| Record | Contents | Owner |
| --- | --- | --- |
| `.agent-runs/ROUND/round.json` | Version, ID, pinned base, open/closed, assignments and outcomes | Coordinator |
| `prompts/A1.md` | Complete assignment with identity, scope, resources and acceptance | Planner, immutable after delivery |
| `results/A1-1.json` | Assignment/base/packet identity, candidate head, PR and check evidence | Executor submits; coordinator imports |

The round manifest is the only runtime status record. Markdown carries scope and reasoning. No
supervisor must interpret prose to guess completion. The CLI records JSON with version 1; unknown
manifest versions fail. Project semantics such as priority labels and lane names stay in assignment
prose/config rather than a mandatory taxonomy. Paths remain configurable for authoritative documents;
local round artifacts use the fixed `.agent-runs/` convention.

An assignment is `assigned`, `result-ready`, `merged` or `cancelled`. Review findings live in the PR
at the actual head. A repair creates a new result, preserving earlier results and requiring fresh
review. A scope change requires explicit cancellation and a new assignment/branch. A new base needs
a later round, after reconciling this one. Terminal assignments
cannot be overwritten. A round remains `open` through planning, review and reconciliation; only
successful closure makes it `closed`.

## Mechanical scaffolding

Use `python3 scripts/round.py` from the coordinator checkout, or supply `--repo /path/to/repo` before
the subcommand. `init`, `assign`, `record`, `resolve`, `close` and `status` are explained in the
[worked example](examples/one-round.md) and individual [phase procedures](.agent/commands/plan-round.md).
Initialization requires a clean checkout and ignored runtime directory.
The CLI creates a self-contained packet and binds its exact UTF-8 bytes with one SHA-256. The packet
contains the round, assignment, base and branch; results repeat the packet digest and base. It checks
those identities on import and retains each submitted result separately. Checks describe the candidate
head at the top of the result; RED history belongs in linked evidence, not the candidate's final gates.

Run writes serially from one coordinator; this is not a distributed service or locking system.
Manifest writes use atomic replacement. If interrupted between artifact creation and manifest update,
inspect both before resuming; an existing unmatched artifact is refused rather than overwritten.
Do not manually mutate submitted packets/results. The result is a claim: a reviewer verifies it.
The CLI does not execute result-provided commands or trust a PR reference as proof of an actual merge.

Before recording `merged`, the reviewer checks current PR head, independent review, complete required
gates and merge authority. `resolve` checks the submitted head, reported check statuses and local
merge commit existence. It cannot detect omitted checks, fabricated evidence or an incorrect PR-to-
merge relationship. Before cancellation, stop the worker and release its mutable resources safely.
Shared-resource coordination is a planner responsibility; no named lane implies a runtime lock.

## Reconciliation is the completion gate

Before closure, verify final combined state, account for all merged/cancelled assignments, stop any
remaining workers, update backlog/details/decisions, and commit a short reconciliation report. Include
negative findings, remaining work, untested operating envelope and the actual behavior delta. A failed
required gate keeps the round open. Do not silently edit the target to match implementation.

The CLI requires terminal outcomes, supplied merges reachable from final main, a nonempty report
committed at that revision, and a bounded handoff naming the same full SHA. The caller supplies final
verification evidence. These presence/identity checks support review; they do not judge report truth,
required-gate completeness, resource release, or whether the chosen ref really is remote main.

`init` refuses another round while any local round remains open. Cancelling work does not waive
reconciliation. Only after closure should the planner session end and a new one start. No automated
supervisor is required; a human or agent can drive each phase.

## Recovery and limits

Takeoff reconstructs from Git, canonical records, PRs and the local ledger. Handoff is advisory:
keep it at most 50 lines / 500 words with full Main-SHA, UTC timestamp and next action. Durable evidence
must also live in PRs or tracked files so lost local records are recoverable. If the ledger is lost,
reconstruct and inspect active workers before initiating anything; the CLI cannot detect remote orphaned
work. Do not blindly replay a command that may have changed state.

A fresh planner without prior chats must be able to name the remaining work, assigned branch/head,
required evidence and next permitted action. The tests exercise ledger behavior in temporary Git
repositories; they do not prove a live runner's recovery or external branch-protection policy.

Config uses TOML for project paths and verification argv. The CLI itself does not execute or require
that config: the phase procedures use it for engineering decisions and checks. This keeps scaffolding
independent of a particular test runner, hosting provider or agent vendor.
