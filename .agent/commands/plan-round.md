# plan-round

Follow [the shared contract](common.md).

Input: desired maximum parallelism or named executable items; default to one assignment.

1. Read the canonical frontier, each candidate's full detail and required architecture sections.
   Select only ready/active unclaimed work with satisfied dependencies. Verify ownership and shared
   seams in source; do not infer parallel safety from disjoint filenames alone.
2. In a clean planner checkout, fetch and fast-forward the default branch without changing unrelated
   work. Pin its full SHA. A stale, diverged or dirty base must be resolved before dispatch.
3. Create a new local round directory with a unique ID and a [round manifest](../../templates/round.toml).
   Use `.agent-runs/<round-id>/round.toml`, `specs/<assignment>.md` and `prompts/<assignment>.md`
   and `results/<assignment>-<attempt>.json`. Validate against the bundled schemas and semantic
   rules in SPEC.md. Never call absent source-project scripts.
4. Use [assign-agent](assign-agent.md) for each task. Reject duplicate IDs/branches, overlapping
   records, incompatible shared contracts or double-booked exclusive resources. Plan fewer lanes
   when necessary. Put later-base or dependent work in a later round.
5. Complete task specs, compute their SHA-256 from actual saved bytes, and render self-contained
   packets using the assignment template. Freeze dispatched specs; changes require explicit revision.
6. Check packets against the originals and the resource/provisioning plan. Output a compact dispatch
   table with item, executor, base, branch, packet location, digest and required resources.

Stop after planning. A packet is not launch authorization. Keep the ledger local; PR metadata and
canonical evidence allow recovery. No merge or target changes occur in this phase.
