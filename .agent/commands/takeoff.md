# takeoff

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Read the project AGENTS.md, `.agent/config.toml`, README orientation and canonical backlog/frontier.
Inspect Git status, known default-branch revision, recent commits and open PRs read-only. Report stale
remote knowledge or unavailable PR access. Do not mutate a dirty checkout during orientation.

Read the optional handoff. Compare its Main-SHA with known main: equal=current, ancestor=stale,
otherwise invalid. Reconstruct missing/stale information from Git, backlog and PR evidence. Inspect
any open round with `python3 scripts/round.py status ROUND`; recover it before planning another.

Output purpose, accepted outcomes, active work/conflicts, decisions owed, next authoritative reads
and handoff freshness. Stop before selecting work. Conversation history is not required input.
