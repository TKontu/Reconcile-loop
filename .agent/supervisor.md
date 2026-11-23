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

1. The supervisor opens tab `round-planner`, starts `claude --session-id <new uuid>` as Herdr agent
   `round-planner`, and submits the round prompt: takeoff, then one full round.
2. The orchestrator's last action is `round_supervisor.py complete --outcome continue`. It refuses
   unless `HANDOFF.md` was written this round and passes `python3 scripts/round.py check-handoff`.
   Herdr's `idle` is never taken as completion, because an orchestrator waiting on CI is idle too.
3. The supervisor sends `/exit`, closes only the tab it created, waits `gap_s`, and starts the next
   round. A new process replaces `/clear`, so the fresh context holds by construction.

## Live work

Long work runs as Herdr lanes in their own `live-<lane>` tabs. The supervisor never touches them.
The round carries such a lane in `HANDOFF.md` instead of waiting, and the next takeoff finds it
there and in `.agent-runs/`. Anything long must be a Herdr lane, because the orchestrator's own
subagents and background commands end with its session.

## The no-endless-wait bound

| Trigger | Default | Response |
|---|---|---|
| Transcript silent (subagents included) | 45 min | Nudge |
| No change in default branch, PR heads or round ledgers | 3 h | Nudge |
| Approval dialog unanswered | 30 min | Notify, refuse with Esc, tell the agent. Never approves |
| Usage limit on screen | up to 6 h | Wait, no nudge spent |
| 3 nudges with no outward progress | | Recycle: new session; takeoff rebuilds from Git |
| Round older than | 12 h | Recycle |
| 2 consecutive recycles, or the default branch unchanged over 3 rounds | | HALT and notify |

Only outward progress refunds nudges, so a session that merely keeps its transcript busy cannot
extend a round forever. `run --set KEY=SECONDS` shortens any timer for a trial.

## Configuration

The supervisor reads `.agent/config.toml`: `[project] default_branch` (default `main`) and an
optional `[supervisor] permission_mode` (default `auto`). Unattended sessions cannot answer
approval dialogs, so the mode must let a round run; the watchdog refuses any dialog left open.
Merges still follow `[policy] merge_authority`: when it is not the planner's, approved PRs are
parked in `HANDOFF.md` and on the dashboard as owed to the operator. `--claude-arg` adds flags to
every session. `ROUND_SUPERVISOR_ROOT` points the supervisor at another checkout.

## Operating it

State lives in `.agent-runs/supervisor/` (`supervisor.log`, `news.jsonl`, `current.json`,
`complete.json`, `HALT`).

```sh
S=scripts/round_supervisor.py
python3 $S run --dry-run          # policy and preconditions; starts nothing
python3 $S up --for 8h            # tab round-loop: supervisor on top, dashboard below
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
planner tab and leaves a dummy `live-*` lane alone; the next round's takeoff lists that lane; a
killed and restarted supervisor adopts the round; then two real rounds and `stop-after-round`.
A stop leaves `HALT`; run `clear-halt` before the next `up`.
