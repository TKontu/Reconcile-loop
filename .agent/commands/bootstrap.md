# bootstrap

Read the project’s existing AGENTS.md and `.agent/config.toml` if present; follow [the protocol](../../SPEC.md).

Input: project repository and its architecture, README and backlog.

1. Inspect existing instructions, files, Git status and verification tools. Preserve user changes.
2. Run the pack's `scripts/install.py` against the project root, adding `--claude`/`--codex` for
   the runner entry points, or copy the same paths manually. Merge every `*.pack-new` file it
   reports into the project's version, then delete it. Preserve relative paths and retain the
   pack’s MIT notice with copied materials; do not replace an existing project’s license.
3. Merge [the project contract](../../templates/AGENTS.md) into the target AGENTS.md; do not copy
   the pattern library's contributor contract. Adapt `.agent/config.example.toml` into
   `.agent/config.toml` with actual architecture/backlog paths, verification argv and merge authority.
   Identify and link the project's existing resource-safety, verification, review/merge and
   publication/privacy policies where applicable. Resolve conflicting instructions before dispatch;
   missing policy decisions remain named setup gaps. Keep these rules in their project sources,
   not copied into this protocol or a second policy document.
4. Preserve the project's README; add a short workflow pointer. Ensure `.agent-runs/` and HANDOFF.md
   are ignored. Keep durable acceptance and decisions in tracked records or PRs.
5. Make one small item executable: approved target references, outcome, boundaries, dependencies,
   acceptance and verification environment. Use [the item template](../../templates/item.md).
6. Check referenced files/tools exist and the configured verification command actually works.
   Report missing decisions explicitly; do not replace placeholders with invented behavior.

Stop with a ready first item or named setup gaps. No dispatch, PR publication or merge is implied.
