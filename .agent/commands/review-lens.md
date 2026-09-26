# review-lens

Follow [the shared contract](common.md).

Input: pinned base/head, changed files, original assignment references, and a named lens.

Inspect code at the supplied revisions, not an unrelated working tree or mutable fetch alias.
- Claims: compare PR claims about behavior, callers and checks with source/evidence.
- Conformance: compare restated rules with their canonical originals, including weakened or stricter drift.
- Correctness: identify concrete failing scenarios; for relocations verify claimed behavior preservation.
- Scope: compare actual edits with assignment boundaries and approved decisions.
- Production path: trace entry points, defaults and producer/consumer seams; test that the cited checks
  exercise those paths and identify untested scale/resource envelopes.

Return what holds, located findings, confidence, severity, missing evidence and scope limits.
Read-only by default. Safe checks may run in an isolated workspace only within the assigned resource
permissions. Do not mutate the author's branch, post comments, push, merge, or reinterpret architecture.
