# resume-round

Follow [the shared contract](common.md).

Input: explicit round or halt record.

Read [supervision](../../docs/supervision.md), halt/log metadata, round packets, Git/PR/check state and
runner identities. Inspect before editing or launching. Inventory acknowledged sends, active workers,
resource ownership, existing branches, actual merged results and the last verified phase artifact.

Identify the cause and next safe step. Preserve assignment IDs/specs; if scope or base must change,
record a planner revision rather than pretending the old packet applies. Never double-dispatch a
worker or release a resource while it may still be using it. A process timeout does not prove exit.

Apply only authorized recovery: stop or retain workers deliberately, repair configuration/evidence,
reverify affected checks, then resume from a proved safe boundary. Clear the halt only when the
cause is resolved and recovery ownership is recorded. If state is unknowable, keep it halted and
report the exact missing evidence. Do not automatically rerun planning or a mutating phase.
