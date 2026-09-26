# handoff

Follow [the shared contract](common.md).

Input: optional named round; use actual current default-branch state.

Inspect the canonical registry, current full main SHA, merged/open PRs and decisions. Fill
[the handoff template](../../templates/handoff.md) at the profile's ignored handoff location.
Include UTC timestamp, full SHA, round delta, active PRs/conflicts, expensive-to-rediscover blockers,
first-execution/scale marker, and one exact next action with authoritative links.

Validate required sections, timestamp parseability, SHA equality to the intended current revision,
links, at most 50 lines and 500 words. Use the project checker if configured, or perform these checks
with available tools. Do not claim that a missing source-project checker ran. Keep full logs,
architecture summaries, copied frontier text, credentials and durable-only-here decisions out.

Report validation and location. Recommend ending the planner session; do not pretend an agent can
clear its own conversation. Canonical records outrank this advisory delta and permit recovery if lost.
