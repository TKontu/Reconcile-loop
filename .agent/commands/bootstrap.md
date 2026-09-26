# bootstrap

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Input: project repository and its architecture, README and backlog.

1. Inspect existing instructions, files, Git status and verification tools. Preserve user changes.
2. Copy or merge `.agent/commands/`, `.agent/config.example.toml`, `scripts/round.py`, `templates/`
   and `SPEC.md`, plus `examples/one-round.md` for its linked walkthrough. Optionally install `.agents/skills/reconcile-loop/` and the `.claude/commands/`
   wrappers. They reference the same procedures. Preserve these relative paths.
3. Merge [the project contract](../../templates/AGENTS.md) into the target AGENTS.md; do not copy
   the pattern library's contributor contract. Adapt `.agent/config.example.toml` into
   `.agent/config.toml` with actual architecture/backlog paths, verification argv and merge authority.
4. Preserve the project's README; add a short workflow pointer. Ensure `.agent-runs/` and HANDOFF.md
   are ignored. Keep durable acceptance and decisions in tracked records or PRs.
5. Make one small item executable: approved target references, outcome, boundaries, dependencies,
   acceptance and verification environment. Use [the item template](../../templates/item.md).
6. Check referenced files/tools exist and the configured verification command actually works.
   Report missing decisions explicitly; do not replace placeholders with invented behavior.

Stop with a ready first item or named setup gaps. No dispatch, PR publication or merge is implied.
