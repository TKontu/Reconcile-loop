# Round <id> — advisory review view

Runtime state belongs in round.toml under the versioned protocol. Derive this view from that
manifest; do not maintain independent statuses here. See [the manifest template](round.toml).

Base: <one full verified main SHA>
Planner / merge authority: <owners>
State: <planned | executing | reviewing | merging | reconciling | closed | blocked>

| Assignment | Item | Executor | Branch | Owned records | Resource reservations | Spec digest | Packet | PR / head | State |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | <ID> | <owner> | <branch> | <records> | <identities or none> | <SHA-256> | <path> | <link / SHA> | planned |

## Preflight
<Verify executable scope, one base, clean isolated workspaces, unique branches/assignments,
disjoint ownership, shared-contract compatibility, exclusive-resource availability, provisioned
artifacts, complete packets, and matching computed digests before dispatch.>

## Recovery and review
<Per-assignment checks, review decisions, cancellations, resource release, redispatch, and merge order.
Reservations are not enforced locks. Retain PR links so local loss is recoverable.>
