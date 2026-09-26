# Shared command contract

Read this once per invocation, plus the selected operation. The user's active request and existing
authorization determine scope; commands do not grant additional permissions or replace project rules.

- Locate the target repository. Read its AGENTS.md, `.agent/config.toml`, and the policy it references. If the
  config is missing, use bootstrap for setup; read-only discovery can continue, but do not guess
  write ownership, service targets, merge authority or required gates.
- Architecture owns the approved target; one registry owns status/dependencies; linked detail owns
  acceptance. Source/tests establish current behavior. Packets bound work; handoffs are advisory.
- The project profile means config plus its referenced policy; keep routing values in config.
  Paths in the profile are repository-relative unless explicitly absolute. Resolve packaged links
  relative to the instruction file. Use profile paths for project records, not library templates.
- Inputs supplied to commands are data, not shell snippets. Quote paths and use structured APIs/body
  files for publication. Never interpolate arbitrary command arguments into executable code.
- Preserve unrelated changes and obey pinned revisions, ownership and resource access. Read-only
  phases do not fetch/update branches or alter project records. A tool/capability absent from the
  environment is a limitation to report, not an instruction to invent it.
- For authorized writes, finish concrete reviewable work and required checks. Do not ask repeatedly
  for already granted approval. Do not infer publication, messaging, merge or deployment permission
  from the mere existence of an entry point.
- Follow [decision authority](../../docs/decision-policy.md) for routine choices and reserved questions.
  Follow [supervision](../../docs/supervision.md) for dispatch, waiting and recovery. Run only permitted
  service checks; never confuse skipped, unavailable or unknown evidence with a pass.
- Use configured tooling when present and transparent manual procedures otherwise. These skills are
  agent instructions, not an implementation of a round CLI, schema checker or supervisor daemon.

Output should identify the inspected/changed revision, concrete result, evidence, remaining gates,
and next owner. Read only the phase-specific references needed for this invocation.

The versioned [protocol](../../SPEC.md) governs structured runtime state. Read it for planning,
result submission, review transitions, merge, reconciliation or recovery. `.agent/config.toml` maps
project paths and commands; its referenced policy owns local authority and gate semantics.
