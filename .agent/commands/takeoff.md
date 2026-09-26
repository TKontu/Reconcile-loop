# takeoff

Follow [the shared contract](common.md).

Input: optional handoff path; otherwise use the project profile.

1. Read the project contract/profile, stable README orientation and current backlog frontier.
2. Inspect working tree, branch, local/remote revisions, recent commits and open PRs. This phase is
   read-only; report stale remote knowledge or unavailable access rather than silently fetching or
   modifying the workspace.
3. Compare handoff main SHA with the known main revision: equal=current, ancestor=stale,
   non-ancestor=invalid. For stale handoffs inspect intervening changes. Missing/invalid handoff is
   recoverable from Git, canonical records and PR evidence; it is not a substitute status registry.
4. Produce a brief: purpose and flows, maturity, recent changes, active PR/conflict map, current
   frontier and decisions owed, handoff freshness, and next authoritative reads.
5. Stop before selecting work or reading unrelated architecture/history. Planning is a separate phase.
