# Pattern catalog

## Authority and progressive context

The architecture defines the approved target. One backlog registry defines current status and
dependencies; linked item records define complete acceptance. Approved decisions govern exceptions.
Source and tests establish actual implementation behavior. A discrepancy between actual and target
is a finding to resolve, not permission to rewrite the target. Prompts constrain assignments;
handoffs and navigation indexes are advisory. Agent conversation is never required project memory.

Read stable orientation, the current frontier, the assigned row and its entire detail, then the
specific architecture sections needed for the decision. Broaden only when conflicts or cross-cutting
work require it. Verify search/index claims in source. Keep successful output short, but retain
failure diagnostics and acceptance gaps.

## Bounded assignments and isolated execution

The planner owns selection, dependencies, governance IDs, shared frontier text, and merge order.
Executors own only assigned code and records. Each packet names a verified base commit, branch,
objective, non-goals, authoritative references, resources, acceptance, and verification owner.
It must work when pasted into a fresh checkout without planner-local files.

Use separate clones or worktrees. A dirty executor workspace, unexpected base, missing artifact,
changed spec, or ownership collision stops dispatch until resolved. Never silently substitute a
new base or transfer a failed executor's assignment to a second active executor.

For batches, bind a packet to the exact UTF-8 bytes of its task spec with SHA-256, computed by a
standard hashing tool. Include that digest in the packet and PR; compare it with the original spec
at review. A digest detects mismatches, not authorization or semantic correctness. Freeze dispatched
specs; any revision requires explicit replanning and review of affected evidence.

## Resources, not just files

Disjoint files do not guarantee independent work. Check shared contracts, produced/consumed data,
fixtures, migrations, and stateful services. Reserve each exclusive resource for one active owner;
use independent resource identities so unrelated test services need not serialize.

A useful local taxonomy is offline, disposable integration, and persistent/live. Offline means no
mutable-service access; explicitly authorized stateless inference can be allowed by project policy.
Declare shared capacity constraints as well as mutation rights. Protect persistent data with explicit
reset authorization, target guards, and recovery procedures. A written lease is not a runtime lock.

## Evidence has a scope

Use test-first development for behavior changes: show the intended failure, make the smallest fix,
and run surgical checks. Run the project's broad local gate once before the PR; repeat relevant
checks after subsequent changes or failures. Required checks must apply to the actual reviewed head.
Expensive integration can be deferred until merge-ready, with an exact-head trigger and result.
After serial merges, validate the combined final revision before closing the round.

Green unit CI does not prove integration, a skipped live suite does not prove live behavior, and
small fixtures do not prove production scale. Record environment, commands, counts, skips, tested
cardinality, and untested envelope. An offline implementation still names an owner for owed service
verification. A sibling's integration run does not test another branch's changes.

## Review connections and scale

For every new public symbol, identify its production caller or a named follow-up wiring item.
For every changed data shape, identify producer and consumer and exercise their boundary together.
For collection-sized work, review bounded query parameters, memory, transaction duration, and
checkpoint cadence. Track which stages have never run at representative scale.

Prefer the smallest implementation meeting current requirements. Reuse existing capabilities.
New flags, fallbacks, and dual paths need owners and retirement gates. Tactical debt needs a named
successor item. Review depth should follow risk; mechanical monitoring need not use the same model
budget as architecture or concurrency review.

## Reconciliation creates the next plan

Completion means the stated acceptance passed, not that every ambition is proven. Record negative
results and residuals. Keep present status single-valued; use a dated ledger for superseded rulings
and measurements, and Git history for ordinary replaced prose. Decisions have one canonical full
statement, with pointers elsewhere.

A result may close an item, reveal a dependency, require an investigation, or challenge the target.
A failed experiment is evidence; intentional divergence is a recorded deviation; a proposed target
change requires approval before execution. Reconciliation routes each result and updates the frontier.
A fresh session then reconstructs current state without inheriting old conversational assumptions.
