"""Pure next-action decision for the supervisor.

`decide(snapshot)` reads one observation snapshot (see observe.py) and returns exactly one action.
It performs no I/O. Rules, first match wins:

1. Ledger shape: more than one open round stops; a version 1 open round is parked as manual.
2. Containment of live sessions, even while halted: kill past deadline, mark lost, acknowledge.
3. An uncleared halt parks the supervisor. A dirty or diverged coordinator checkout stops it.
4. Settle finished work: import an exited session, verify an in-flight merge.
5. No open round: stall, run limit and autonomy checks, else start the next round.
6. Planning: launch one planner while the round has no assignments.
7. Per assignment, aggregated as Merge > LaunchReviewer > LaunchExecutor > Cleanup within the
   parallel and budget limits; a hold on one assignment never blocks another.
8. Round end: reconcile, run the final gate and close, as autonomy allows.

Exit codes: 0 action, wait or routine park; 10 needs attention; 11 transient or unknown.
"""

from datetime import datetime, timezone

from .policy import merge_gate

LIVE_SESSION = {"launching", "running"}
TERMINAL = {"merged", "cancelled"}
ATTENTION_PARKS = {"halted", "stalled", "budget"}


def action(kind, exit=0, **fields):
    return {"kind": kind, "exit": exit, **fields}


def epoch(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def park(reason, **fields):
    return action("Park", 10 if reason in ATTENTION_PARKS else 0, reason=reason, **fields)


def latest_review(assignment):
    if not assignment["results"]:
        return None
    current = [r for r in assignment["reviews"] if r["result"] == assignment["results"][-1]]
    return current[-1] if current else None


def next_round_id(ids):
    numbers = [int(i[1:]) for i in ids if i[:1] == "R" and i[1:].isdigit()]
    candidate = max(numbers, default=0) + 1
    while f"R{candidate}" in ids:
        candidate += 1
    return f"R{candidate}"


def contain(snapshot, sessions):
    """Return the most urgent containment action for live agent processes, if any."""
    now = snapshot["now"]
    grace = snapshot["limits"]["launch_grace_seconds"]
    found = {}
    for name, record in sorted(sessions.items()):
        if record["state"] not in LIVE_SESSION or record["role"] == "merger":
            continue
        process = snapshot["processes"].get(name) or {"pid": None, "alive": False, "exit": None}
        if process["exit"] is not None:
            continue
        if process["alive"] and now > epoch(record["deadline_utc"]):
            found.setdefault("KillSession", name)
        elif not process["alive"] and (
            record["state"] == "running" or now - epoch(record["started_utc"]) > grace
        ):
            found.setdefault("MarkLost", name)
        elif process["alive"] and record["state"] == "launching":
            found.setdefault("AckSession", name)
    for kind in ("KillSession", "MarkLost", "AckSession"):
        if kind in found:
            name = found[kind]
            return action(kind, session=name, pid=(snapshot["processes"].get(name) or {}).get("pid"))
    return None


def settle(snapshot, sessions):
    for name, record in sorted(sessions.items()):
        if record["state"] not in LIVE_SESSION or record["role"] == "merger":
            continue
        process = snapshot["processes"].get(name) or {}
        if process.get("exit") is not None:
            return action("ImportSession", session=name, role=record["role"])
    for name, record in sorted(sessions.items()):
        if record["state"] in LIVE_SESSION and record["role"] == "merger":
            return action("VerifyMerge", session=name, assignment=record["assignment"])
    return None


def start_round(snapshot):
    limits = snapshot["limits"]
    closed = snapshot["rounds"]["closed"]
    recent = closed[-limits["stall_rounds"] :]
    if len(recent) == limits["stall_rounds"] and all(r["delta"] == "none" for r in recent):
        return park("stalled", rounds=[r["id"] for r in recent])
    if snapshot["rounds_this_run"] >= limits["max_rounds_per_run"]:
        return park("max-rounds")
    if snapshot["autonomy"] < 3 and not snapshot["new_round"]:
        return park("no-round")
    return action(
        "InitRound",
        round_id=next_round_id(snapshot["rounds"]["ids"]),
        base=snapshot["remote"]["default_sha"],
    )


def evaluate(snapshot, aid, a, notes):
    """Return a candidate action for one idle assignment, or record why there is none."""
    state = a["state"]

    def hold(reason):
        notes["holds"].append({"assignment": aid, "reason": reason})
    if state in TERMINAL:
        tree = snapshot["worktrees"].get(aid)
        if tree and tree["exists"]:
            if tree["dirty"]:
                return hold("worktree-dirty")
            return action("Cleanup", assignment=aid)
        return None
    if state == "assigned":
        return action("LaunchExecutor", assignment=aid, repair=False)
    if state == "blocked":
        return hold("result-blocked")
    head = snapshot["results"][aid]["head_sha"]
    observed = snapshot["prs"].get(aid) or {"unknown": "not observed"}
    if "unknown" in observed:
        notes["unknown"].append({"assignment": aid, "reason": observed["unknown"]})
        return None
    pr = observed["pr"]
    if pr is None:
        return hold("pr-missing")
    if pr["state"] == "MERGED":
        return hold("merged-externally")
    if pr["state"] != "OPEN":
        return hold("pr-closed")
    if pr["headRefOid"] != head:
        return hold("head-moved")
    review = latest_review(a)
    if review is None:
        return action("LaunchReviewer", assignment=aid, head=head)
    if review["verdict"] == "needs-fix":
        if len(a["results"]) - 1 >= snapshot["limits"]["max_repairs"]:
            return hold("repairs-exhausted")
        return action("LaunchExecutor", assignment=aid, repair=True)
    if review["verdict"] != "ready":
        return hold("review-blocked")
    if snapshot["autonomy"] < 2:
        notes["parks"].append({"assignment": aid, "reason": "awaiting-merge"})
        return None
    checks = snapshot["checks"].get(aid) or {"unknown": "not observed"}
    if "unknown" in checks:
        notes["unknown"].append({"assignment": aid, "reason": checks["unknown"]})
        return None
    diff = snapshot["diffs"].get(aid) or {"files": None, "changed_lines": 0}
    timeout = snapshot["limits"]["ci_timeout_minutes"] * 60
    facts = {
        "kind": a["kind"],
        "branch": a["branch"],
        "default_branch": snapshot["default_branch"],
        "result_head": head,
        "review": review,
        "pr": pr,
        "checks": checks["state"],
        "checks_timed_out": snapshot["now"] - epoch(review["utc"]) > timeout,
        "files": diff["files"],
        "changed_lines": diff["changed_lines"],
        "binary": diff.get("binary", []),
        "owned_paths": a["owned_paths"],
    }
    verdict, reasons = merge_gate(facts, snapshot["gate"])
    if verdict == "merge":
        return action("Merge", assignment=aid, head=head)
    for reason in reasons:
        (notes["holds"] if verdict == "hold" else notes["waits"]).append(
            {"assignment": aid, "reason": reason}
        )
    return None


def finish_round(snapshot, assignments):
    reconcile = [a for a in assignments.values() if a["kind"] == "reconcile"]
    if any(a["state"] == "merged" for a in reconcile):
        gate = snapshot["final_gate"]
        if gate is None:
            return action("RunFinalGate")
        if gate == "passed":
            return action("CloseRound")
        return action("Hold", 10, holds=[{"assignment": None, "reason": "final-gate-failed"}])
    if snapshot["autonomy"] < 3:
        return park("awaiting-reconcile")
    if reconcile:
        return action("Hold", 10, holds=[{"assignment": None, "reason": "reconcile-cancelled"}])
    return action("CreateReconcile", start=snapshot["remote"]["default_sha"])


def decide(snapshot):
    rounds = snapshot["rounds"]
    if len(rounds["open"]) > 1:
        return action("Stop", 10, reason="multiple-open-rounds", rounds=rounds["open"])
    manifest = snapshot["round"]
    if manifest and manifest["version"] != 2:
        return park("manual-round", round=manifest["id"])
    sessions = manifest["sessions"] if manifest else {}
    found = contain(snapshot, sessions)
    if found:
        return found
    if manifest:
        halts = [h["id"] for h in manifest["halts"] if not h["cleared_utc"]]
        if halts:
            return park("halted", halts=halts)
    if not snapshot["checkout"]["clean"]:
        return action("Stop", 10, reason="dirty-checkout")
    if snapshot["remote"]["default_sha"] is None:
        return action("Unknown", 11, reason=snapshot["remote"]["unknown"])
    if snapshot["checkout"]["head_on_default"] is None:
        return action("Fetch")
    if not snapshot["checkout"]["head_on_default"]:
        return action("Stop", 10, reason="diverged-checkout")
    if not manifest:
        return start_round(snapshot)
    found = settle(snapshot, sessions)
    if found:
        return found

    limits = snapshot["limits"]
    workers = [s for s in sessions.values() if s["role"] != "merger"]
    live = [s for s in workers if s["state"] in LIVE_SESSION]
    spent = sum(s.get("cost_usd") or 0 for s in workers)
    budget_left = len(workers) < limits["sessions_per_round"] and spent < limits["round_usd"]
    slots = limits["max_parallel"] - len(live)
    assignments = manifest["assignments"]

    if not assignments:
        if any(s["role"] == "planner" for s in live):
            return action("Wait", reason="planner-running")
        if any(s["role"] == "planner" for s in workers):
            return action("Hold", 10, holds=[{"assignment": None, "reason": "planner-produced-nothing"}])
        if not budget_left:
            return park("budget")
        return action("LaunchPlanner")

    notes = {"holds": [], "waits": [], "unknown": [], "parks": []}
    busy = {s["assignment"] for s in live}
    candidates = []
    for aid in sorted(assignments):
        if aid in busy:
            notes["waits"].append({"assignment": aid, "reason": "session-running"})
            continue
        found = evaluate(snapshot, aid, assignments[aid], notes)
        if found:
            candidates.append(found)
    extras = {"holds": notes["holds"]} if notes["holds"] else {}
    launch_blocked = False
    for kind in ("Merge", "LaunchReviewer", "LaunchExecutor", "Cleanup"):
        for found in candidates:
            if found["kind"] != kind:
                continue
            if kind.startswith("Launch"):
                if slots < 1:
                    notes["waits"].append({"assignment": found["assignment"], "reason": "parallel-limit"})
                    continue
                if not budget_left:
                    launch_blocked = True
                    continue
            return {**found, **extras}

    if all(a["state"] in TERMINAL for a in assignments.values()) and not notes["holds"]:
        return finish_round(snapshot, assignments)
    if notes["holds"]:
        return action("Hold", 10, holds=notes["holds"])
    if notes["unknown"]:
        return action("Unknown", 11, reason="observation-unavailable", unknown=notes["unknown"])
    if notes["waits"]:
        return action("Wait", waits=notes["waits"])
    if launch_blocked:
        return park("budget")
    if notes["parks"]:
        return park("awaiting-merge", assignments=[p["assignment"] for p in notes["parks"]])
    return action("Hold", 10, holds=[{"assignment": None, "reason": "no-rule-matched"}])
