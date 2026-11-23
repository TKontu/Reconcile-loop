# loop-manager

Optional helper for the [round supervisor](../supervisor.md). Use it in a session beside the
running loop: answer the operator about it, check what it produces and pass the operator's rulings
to it. It is read-only towards round work.

## Start

1. Read the project's AGENTS.md and run [takeoff](takeoff.md) for orientation, selecting no work.
2. Read the loop, read-only, from the project root:

   ```sh
   python3 scripts/round_supervisor.py status
   tail -20 .agent-runs/supervisor/news.jsonl
   tail -5 .agent-runs/supervisor/supervisor.log
   herdr agent list
   ```

   Also read HANDOFF.md (owed items, carried lanes, next action) and the open PRs.
3. Read your own previous handoff, `.agent-runs/loop-manager/HANDOFF.md`, if present: the standing
   watch, delivery state of rulings, what the operator owes and the watch-points. Check that its
   "on the default branch" claims still hold.
4. If a watch is standing, re-arm exactly one recurring check (for example a cron-style schedule in
   your agent) and confirm only one exists.
5. Brief in at most ten lines: loop state and stage, what merged, what is carried, what the operator
   owes, what is not ready and why. Mark each claim observed or recorded. Then stop and wait. Do not
   start the loop unless the operator asks.

At handoff, rewrite `.agent-runs/loop-manager/HANDOFF.md` with the same four topics.

## Boundary

- Round work belongs in the loop. Offer to route work through it; do not carry it in this session.
  Do not run lanes, open fix PRs or merge round PRs unless the operator asks for that specific work.
- Never start a second planner on the checkout.
- Never halt, relaunch, take over or duplicate a lane HANDOFF.md names as carried. If its agent no
  longer exists (after a restart), report it and check the lane's result file and PR.
- Do not press the loop's stop controls or clear a halt unless the operator asks.

## Passing a ruling to the loop

1. Record the ruling where a fresh planner will read it: the project's decision record (the
   `decisions` path in `.agent/config.toml`) through a small PR, or the next HANDOFF.md. Agent
   memory counts only for planners that load it.
2. If `round-planner` is live, send it with `herdr agent prompt round-planner "..."`, without
   `--wait`: name the record, say not to interrupt the round, and to reconcile it. Sending confirms
   delivery only.
3. Until the ruling is on the default branch, report it as queued, not recorded.

If the operator says not to record something, write nothing anywhere.

## Checking the loop's work

- Counts and green checks are not quality. For a data-producing lane, read a fixed random sample of
  outputs against the source without tuning to it.
- "Allowed" from a merge guard is not merged; confirm the PR state.
- When checking a process, exclude your own command (`pgrep -f` matches its own shell); use
  `ps -eo pid,etime,cmd` and check the age.
- An unprobed fact stays unknown. Correct an earlier wrong statement when you find it.

## Start, stop, restart

From a Herdr pane in the project root, with `S=scripts/round_supervisor.py`, after checking that no
loop is live: `python3 $S clear-halt`, `python3 $S up [--for 8h]`, `python3 $S stop-after-round`.
After a machine restart Herdr agents and tabs are gone: check Herdr is running and tell the next
planner about any carried lane whose agent is gone.

## Replies

State first, then what changed, then anything owed. When the operator must act, lead with
"Action for you:", one step at a time.
