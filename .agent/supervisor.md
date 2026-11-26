# Optional round supervisor

`scripts/round_supervisor.py` runs the loop unattended: one fresh Claude Code session per round,
started and watched inside the Herdr terminal multiplexer. It is an add-on. The protocol, the phase
procedures and `scripts/round.py` never depend on it; delete the script and the loop still runs by
hand. The supervisor itself is a plain process with no LLM; the only model is the per-round
orchestrator it starts.

Requirements: a POSIX system, Python 3.11+, `herdr`, `claude` and an authenticated `gh`, with the
project bootstrapped (`.agent/config.toml` present, `.agent-runs/` ignored). Commands run from a
Herdr pane (`HERDR_ENV=1`) in the project root.

## How a round turns over

1. The supervisor opens tab `round-planner-<repo>`, starts `claude --session-id <new uuid>` as Herdr
   agent `round-planner-<repo>`, and submits the round prompt: takeoff, then one full round.
2. The orchestrator's last action is `round_supervisor.py complete --outcome continue`. It refuses
   unless `HANDOFF.md` was written this round and passes `python3 scripts/round.py check-handoff`.
   Herdr's `idle` is never taken as completion, because an orchestrator waiting on CI is idle too.
3. The supervisor sends `/exit`, closes only the tab it created, waits `gap_s`, and starts the next
   round. A new process replaces `/clear`, so the fresh context holds by construction.

## Live work

Long work runs as Herdr lanes in their own `live-<repo>-<lane>` tabs, opened in the supervisor's
workspace. Lanes never create Herdr workspaces. The supervisor never touches them.
The round carries such a lane in `HANDOFF.md` instead of waiting, and the next takeoff finds it
there and in `.agent-runs/`. Anything long must be a Herdr lane, because the orchestrator's own
subagents and background commands end with its session.

`scripts/lanes.py` gives lanes a lifecycle the round prompt follows. It needs no LLM, and the
supervisor only reads its records for the dashboard.

```sh
L=scripts/lanes.py
python3 $L start sweep --cwd ../proj-lanes/sweep --cmd run_sweep.sh   # or --agent claude|codex
python3 $L status            # running, done, recorded, blocked, dead (with its resume command), unknown
python3 $L recorded sweep --note "round 12, PR #40"
python3 $L cleanup           # dry run; --go acts
```

- `start` opens the tab in `$HERDR_WORKSPACE_ID` and refuses a name already in Herdr or a lane
  that is still running. A `--cmd` lane runs under a wrapper that writes `runner.pid`,
  `runner.log` and `runner.rc` (exit code and time) under `.agent-runs/lanes/<lane>/`, next to the
  `lane.json` record. Outside Herdr a `--cmd` lane is detached with `setsid -f nohup`.
- `status` never reads Herdr's `idle` as finished: an idle agent lane stays `running` until its
  result and PR are checked and it is marked `recorded`. A recycled pid reads as gone.
- `cleanup --go` runs after `/merge-round` and before `/handoff`. It closes a lane tab only when
  every pane in it is settled, the lane is not carried in `HANDOFF.md`, its record (if any) is
  `done` or `recorded`, and its worktree is finished or gone. A tab carried by name protects its
  worktree as well. It then removes, with plain `git worktree remove`, each lane worktree (a
  sibling `<repo>-...` path or a recorded lane cwd) whose newest PR is merged or closed and none is
  open. It holds and reports anything carried, dirty, unpushed, busy, without a PR or still live.
  Protected tabs (planner, loop, supervisor, manager, review server), other repos' tabs and tabs
  outside the lane paths are never closed. The round carries every held lane with its reason.

## The no-endless-wait bound

| Trigger | Default | Response |
|---|---|---|
| Transcript silent (subagents included) | 45 min | Nudge |
| No change in default branch, PR heads or round ledgers | 3 h | Nudge |
| Approval dialog unanswered | 30 min | Notify, refuse with Esc, tell the agent. Never approves |
| Usage limit on screen | up to 6 h | Wait, no nudge spent |
| 3 nudges with no outward progress | | Recycle: new session; takeoff rebuilds from Git |
| Round older than | 12 h | Recycle |
| 2 consecutive recycles, or the default branch unchanged over 3 rounds | | Diagnosing round (below) |
| A planner's `complete --outcome halt` | | Diagnosing round (below) |
| A planner's `complete --outcome wait --cause C [--until T]` | up to 12 h | Wait until T, then diagnose again |
| The same cause unresolved twice in a row (a planner's halt or wait cause, or the breaker's own `no-advance`/`recycled` when a diagnosing round left the default branch unmoved) | | HALT and notify, naming the cause |
| Operator `stop` or `stop-after-round` | | HALT |

**Diagnosing rounds.** A loop that makes no progress is fixed by reconciliation, not by retry or a
bare halt. When the breaker trips or a planner asks to halt, the next round's prompt starts with a
diagnosing preamble: reconcile the failed or empty rounds; classify the cause with evidence
(`executor-limit`, `backlog-exhausted`, `blocked-on-operator`, `tool-broken`, `lanes-failing` or
`other`); act on it (switch harness, re-rank or split items, repair a tool, turn a block into a
precise owed item); then plan whatever that unlocks. Only when an external event alone can unblock
every lane does the round end with `wait`, naming the cause and, if known, when it clears (ISO
time; capped at `wait_max_s`). The stop controls are obeyed during a wait. A halt or wait without
`--cause` is refused; a missing cause in a sentinel counts as `unspecified`. A wait whose `until`
is still in the future is pending, not unresolved, so a multi-day limit waits in `wait_max_s`
steps without halting; once its time has passed the same cause escalates. Only an advance of the
default branch resets the cause count; a round ending `continue` without moving it does not. The diagnosing state is held in memory, so a supervisor
restarted mid-diagnosis forgets the previous cause.

Only outward progress refunds nudges, so a session that merely keeps its transcript busy cannot
extend a round forever. `run --set KEY=SECONDS` shortens any timer for a trial.

## Configuration

The supervisor reads `.agent/config.toml`: `[project] default_branch` (default `main`) and an
optional `[supervisor] permission_mode` (default `auto`). Unattended sessions cannot answer
approval dialogs, so the mode must let a round run; the watchdog refuses any dialog left open.
Optional `[supervisor] lane_harnesses` lists executor harnesses in order of preference, with
launch templates in `[supervisor.harness_commands]` (see `.agent/config.example.toml`). When it is
set, the round prompt tells the planner to start each lane with the first available harness, to
move to the next when one hits a usage limit or is refused (never to wait or halt over it), to
record the harness per lane in `HANDOFF.md`, and to open lane tabs with `--cwd <lane worktree>`.
Without the key the prompt is unchanged. Merges still follow `[policy] merge_authority`: when it is not the planner's, approved PRs are
parked in `HANDOFF.md` and on the dashboard as owed to the operator. `--claude-arg` adds flags to
every session.

Herdr agent names are global across projects, so every name the supervisor uses carries the repo
slug: `[supervisor] name` if set, else the checkout's directory name (lowercased, non-alphanumerics
as `-`). Several repos can then run loops side by side. Two checkouts with the same directory name
need distinct `[supervisor] name` values; `run --dry-run` and `status` print the names, and the
supervisor refuses to adopt a planner agent whose working directory is another checkout. Tabs are
created with `--workspace "$HERDR_WORKSPACE_ID"` (the supervisor's own workspace), never the
focused one, and `run` refuses without that variable. `ROUND_SUPERVISOR_ROOT` points the supervisor at another checkout.

## Running unattended

The watchdog never approves a dialog, so every action a round needs must already be allowed.
Check each item before a long `up`:

1. **Merge delegation.** Either keep merges with the operator (approved PRs are parked as owed),
   or delegate them: set `[policy] merge_authority` as in the commented example in
   `.agent/config.example.toml`, so the planner merges only through `scripts/merge_guard.py`, and
   deny raw `gh pr merge` in your agent settings. The guard leaves operator-owned paths to you;
   keep those to the permission rules, the guard itself and any gate or verdict records your
   project keeps (`[merge_guard] operator_paths`).
2. **Allow rules.** Add the commands rounds and lanes run to your local agent settings yourself;
   [`templates/settings.local.example.json`](../templates/settings.local.example.json) is an
   example to merge into `.claude/settings.local.json`. Agents cannot add permission rules for
   themselves, and must not be asked to. `herdr pane run:*` is broad: it types any command into
   any pane, so allow it only where that is acceptable, or narrow it.
3. **Harnesses.** List the executor harnesses you have in `[supervisor] lane_harnesses`, each
   with a non-interactive launch template, so a usage limit on one moves lanes to the next.
   Codex's `-s workspace-write` sandbox needs unprivileged user namespaces (bwrap) and fails on
   hosts that block them; there use its approval-free mode (`--approve-for-me` in the example)
   inside the lane worktree instead.
4. **Lane release.** Rounds run `scripts/lanes.py cleanup --go`; it closes a finished lane's idle
   tabs before removing its worktree, so the tab's shell does not pin the tree, and holds tabs
   outside a registered lane worktree. Nothing else to configure.
5. **Stop controls.** Use `up --for <duration>` or `stop-after-round`; a halt names its cause in
   `HALT` and on the dashboard. Expect a halt when the same cause survives two diagnosing rounds:
   a round that ends `continue` without advancing the default branch does not reset the count.

## Operating it

State lives in `.agent-runs/supervisor/` (`supervisor.log`, `news.jsonl`, `current.json`,
`complete.json`, `HALT`).

```sh
S=scripts/round_supervisor.py
python3 $S run --dry-run          # policy and preconditions; starts nothing
python3 $S up --for 8h            # tab round-loop-<repo>: supervisor on top, dashboard below
python3 $S status
python3 $S stop-after-round       # the normal stop
python3 $S stop-in 2h
python3 $S stop                   # halt at the next poll; the orchestrator keeps its tab
python3 $S clear-halt             # also clears stop flags and any deadline
```

The dashboard shows state, time limit, lanes, items owed by the operator and a scrollable news feed
(`j`/`k`); `s` toggles stop-after-round and `q` closes only the view. The orchestrator fills the feed
with `note` (at most 140 characters). A restarted supervisor adopts the open round rather than
starting another. `run` refuses if another Claude session is working in the checkout
(`--allow-other` overrides), if `HALT` exists, or if another supervisor holds the lock.

To watch the loop from a separate session, use the [loop-manager](commands/loop-manager.md) helper.

## First run

Check each step before the next: `--dry-run` finds the transcript directory and a working
fingerprint; one `up` round reaches `complete` only after a valid handoff; turnover closes only the
planner tab and leaves a dummy `live-<repo>-*` lane alone; the next round's takeoff lists that lane
and `lanes.py status` reports it; `lanes.py cleanup` holds it while carried and releases it once
finished; a
killed and restarted supervisor adopts the round; then two real rounds and `stop-after-round`.
A stop leaves `HALT`; run `clear-halt` before the next `up`.
