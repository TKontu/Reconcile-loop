# pipeline-review

Follow [the shared contract](common.md).

Input: endpoint, command, event handler or other production entry point.

Locate actual routing/wiring and trace validation, authorization, dependencies, transformations,
service/data access, transaction boundaries and response/output handling in source. Verify both ends
of data shapes and errors; identify configured defaults, dead branches, timeouts, retries, idempotency,
resource bounds and durable checkpoints relevant to this path. Compare test entry points with the
real production path rather than assuming unit coverage proves integration.

Return a concise source-linked flow and concrete findings with failing scenario and severity. Mark
unknown/unverified behavior explicitly. Use only authorized environments for reproductions. Read-only
unless fixes or an output artifact are requested; do not scaffold new endpoints or broaden the review
into unrelated architecture. Use the project's stack, not a presumed FastAPI layout.
