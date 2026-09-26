# TASK-001: Document session responses

Target: [approved response contract](../../architecture/target.md).

In scope: a consumer-facing response table in docs/responses.md. No code, defaults, token formats,
database work or target changes. Executor may edit only that document; planner owns status updates.

Acceptance: the table states expired and malformed credentials receive 401; expiry is checked before
resource lookup; valid credentials continue to normal lookup; no inaccessible resource existence leaks.
Run `git diff --check` and independently review the wording against the target. RED/GREEN behavior
tests are N/A for this documentation change. These checks do not prove an implemented endpoint.
