# execute-task

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Input: complete packet and its expected SHA-256, delivered by the planner.

Verify the packet digest, assigned base and branch in a separate clean checkout. Read AGENTS.md,
configuration, full item detail and cited architecture. Resolve missing artifacts or service access
before dependent work; return scope/target conflicts to the planner. Routine authorized implementation
choices do not require repeated approval.

For behavior changes demonstrate the intended failing test, implement the smallest sufficient fix,
and run targeted checks. Documentation uses relevant structural checks. Inspect production callers
and data boundaries when applicable. Run the assigned verification in its safe environment; record
skips/failures honestly. Update only records explicitly assigned to you.

Review the diff for defects, secrets and private material. Commit/push/open a PR when the assignment
or user authorizes publication. Return [result metadata](../../templates/result.json), including the
actual head, packet digest, PR and command evidence. Required acceptance evidence stays in the PR or
tracked reports as well as the local result. The coordinator imports it with:

```sh
python3 scripts/round.py record ROUND --result /path/to/result.json
```

If execution cannot proceed, submit a result through the same command with only `assignment`,
`base_sha`, `packet_sha256`, `status: "blocked"` and a nonempty `reason` describing the missing
requirement and available evidence. No PR, head or completed checks are needed. This leaves the
assignment blocked until a later candidate result or explicit cancellation; it cannot close the round.

A revised head needs another result and review; old results remain available. Stop at the PR and
required executor checks. Never self-merge or claim unrun checks passed.
