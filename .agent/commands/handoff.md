# handoff

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Read current main, canonical backlog, PR outcomes and decisions. Use
[the handoff template](../../templates/handoff.md); include full Main-SHA, UTC timestamp, this round's
delta, active conflicts/blockers, unverified behavior/scale, and one exact next action with links.

Keep it at most 50 lines / 500 words. Validate SHA and links. Do not copy architecture, frontier prose,
full logs, secrets or the conversation transcript. Durable decisions/evidence belong in tracked files
or PRs. The local ignored handoff is advisory and may be reconstructed if lost.

Report its location and remaining gates. End the planner session after reconciliation; do not claim
to clear your own conversation. A fresh planner should recover using only repository/PR records.
