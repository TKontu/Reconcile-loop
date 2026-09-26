# bootstrap

Follow [the shared contract](common.md).

Input: target repository and any supplied architecture, README, backlog, and preferences.

1. Inspect the target's existing instructions, working tree, tracked files, tools, CI and Git remote.
   Inventory before copying. Preserve existing user changes and all project-specific authoritative text.
2. Read the supplied architecture, README orientation and backlog execution contract/frontier. Identify
   actual filenames and case; do not assume README.md and readme.md are interchangeable.
3. Merge the [project contract](../../templates/AGENTS.md) into the target's AGENTS.md. Never copy
   the pattern library's contributor AGENTS.md as the project's operating contract.
4. Install this pack's `.agents/skills/`, `.claude/commands/`, `.agent/`, `docs/agents/`, `SPEC.md`, referenced root-level
   workflow guides, and `templates/`, preserving their relative paths. Compare colliding files and
   merge deliberately; do not replace an existing project's instructions wholesale. Other runners
   can read the canonical command documents directly. Keep vendor bridge files as pointers.
5. Create `.agent/config.toml` from [the config](../../templates/config.toml) and project policy
   from [the checklist](../../templates/project.md). Discover real
   check commands and environments from the target; mark unknown required settings unresolved, never
   invent a passing gate. Map its architecture, registry, details, decisions, evidence and handoff.
6. Establish role/merge authority and standing decision policy from existing user authorization.
   Ask only for material missing decisions; continue independent setup. Configure services only when
   in scope. An absent database or live tier is N/A, not a requirement to add one.
7. Ensure local packets, secrets, handoff and workspace artifacts are ignored without hiding durable
   evidence. Preserve the project's existing ignore rules. Record installation in its README with
   links to the command catalog, keeping the project's own introduction.
8. Prepare one small executable item: measurable outcome, complete detail, canonical references,
   non-goals, ownership and exact verification. Proposed target changes remain non-executable.
9. Validate all installed relative links and entry points; inspect for unresolved required profile
   fields, missing tools and conflicting authority. Report ready or the exact remaining gaps. Do not
   claim readiness based on copied placeholders. Do not dispatch, publish or merge during bootstrap.

Output: installed paths, project profile, first-task readiness, checks performed and unresolved choices.
