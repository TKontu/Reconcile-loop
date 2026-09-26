# review-round

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Read `round.py status ROUND`, original packets, result files and pinned PR diffs. Verify the actual
PR head matches the submitted result and that every required check in the assignment/config ran on
that head. A list of passed checks may still omit a required gate. API errors mean unknown status.

Compare behavior with the target and acceptance. Check concrete failure cases, scope, default changes,
production connections, and resource/scale limits when relevant. Keep review proportional to risk;
multiple agent panels are optional. Record findings with locations and evidence.

Return ready, needs-fix or blocked, with a head-bound review reference. For repairs, send a bounded
request without silently changing the assignment. A new result invalidates the old review. Skipped
or unavailable required checks cannot count as passes. Do not merge during review.

The coordinator records the final reviewed-and-merged outcome only after the separate merge phase.
Review notes live in the PR or a tracked record, not a second editable status registry.
