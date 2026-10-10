# status

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Input: optional item or round identifier. Read-only: edit no file, select no work, open no PR.

Use the configured canonical backlog as the status source, never the README or a handoff. Inspect
known default-branch revision, open PRs, checks and any open round (`python3 scripts/round.py status
ROUND`) without mutating them. Unavailable APIs mean unknown, not "no open PRs" or "checks passed".

Tally statuses from the backlog's actual schema, then spot-check the counts against the file; a parse
that silently misses rows is worse than no number. Per track the project defines, report done/total
with ready, active and blocked counts. Separate items blocked by design (a later gate) from those
blocked on a dependency or open decision. Note active items that are substantially landed and done
items carrying named residual debt.

Then report:

- **Situation**: what recent rounds landed, the critical path, and whether the bottleneck is build,
  measurement or an operator decision; list open decisions.
- **Feasibility**: separate engineering maturity (built and proven to run) from measured operating
  capability; cite recorded numbers, report negative results as-is, and name newly sized risks.
- **Premise check**: for each recent result that may affect the plan, classify it as no change,
  premise shifted with target intact, line of attack exhausted, or target wrong; say whether the
  backlog already routes it or an operator decision is missing.

State the revision and time the report reflects. Surface gaps as recommendations for reconcile or
the operator; do not edit the target or records here.
