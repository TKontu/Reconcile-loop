"""Table-driven checks of the supervisor's pure decision function."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from supervisor.decide import decide  # noqa: E402

NOW = 1_800_000_000  # 2027-01-15T08:00:00Z
BASE = "b" * 40
HEAD = "c" * 40
HEAD2 = "d" * 40
REMOTE = "e" * 40


def utc(offset):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(NOW + offset, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def assignment(state="assigned", kind="work", results=0, reviews=(), branch=None, aid="A1"):
    paths = [f"results/{aid}-{n}.json" for n in range(1, results + 1)]
    return {
        "item": f"TASK-{aid}",
        "branch": branch or f"task/{aid.lower()}",
        "packet": f"prompts/{aid}.md",
        "packet_sha256": "f" * 64,
        "state": state,
        "results": paths,
        "kind": kind,
        "owned_paths": ["docs/**"],
        "resources": [],
        "start_sha": None,
        "reviews": [
            {"result": paths[-1], "head_sha": head, "verdict": verdict, "utc": utc(-600)}
            for verdict, head in reviews
        ],
    }


def session(role, state="running", assignment="A1", started=-60, deadline=3600, cost=None):
    return {
        "role": role,
        "assignment": None if role == "planner" else assignment,
        "session_uuid": f"uuid-{role}",
        "cwd": "/tmp/x",
        "head_sha": None,
        "pid": 42 if state != "launching" else None,
        "started_utc": utc(started),
        "deadline_utc": utc(deadline),
        "state": state,
        "cost_usd": cost,
    }


def open_pr(head=HEAD, **changes):
    return {
        "state": "OPEN",
        "isDraft": False,
        "headRefOid": head,
        "headRefName": "task/a1",
        "baseRefName": "main",
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        **changes,
    }


def snapshot(assignments=None, sessions=None, halts=(), **changes):
    manifest = None
    if assignments is not None:
        manifest = {
            "version": 2,
            "id": "R1",
            "base_sha": BASE,
            "state": "open",
            "assignments": assignments,
            "sessions": sessions or {},
            "halts": list(halts),
        }
    value = {
        "now": NOW,
        "autonomy": 1,
        "new_round": False,
        "rounds_this_run": 0,
        "default_branch": "main",
        "limits": {
            "max_parallel": 1,
            "sessions_per_round": 8,
            "round_usd": 10.0,
            "max_repairs": 2,
            "stall_rounds": 2,
            "max_rounds_per_run": 1,
            "launch_grace_seconds": 120,
            "ci_timeout_minutes": 60,
        },
        "gate": {
            "required_checks": ["check"],
            "protected_paths": [".github/**"],
            "max_changed_lines": 400,
            "allow_reconcile_merge": False,
        },
        "remote": {"default_sha": REMOTE, "unknown": None},
        "checkout": {"clean": True, "head_on_default": True},
        "rounds": {"open": ["R1"] if manifest else [], "closed": [], "ids": ["R1"] if manifest else []},
        "round": manifest,
        "results": {},
        "processes": {},
        "prs": {},
        "checks": {},
        "diffs": {},
        "worktrees": {},
        "final_gate": None,
    }
    for key, item in changes.items():
        value[key] = item
    if manifest:
        for aid, a in assignments.items():
            if a["results"] and aid not in value["results"]:
                value["results"][aid] = {"status": "result-ready", "head_sha": HEAD}
    return value


def ready_for_merge(**changes):
    value = snapshot(
        {"A1": assignment("result-ready", results=1, reviews=[("ready", HEAD)])},
        autonomy=2,
        prs={"A1": {"pr": open_pr()}},
        checks={"A1": {"state": "passed"}},
        diffs={"A1": {"files": ["docs/a.md"], "changed_lines": 3}},
    )
    value.update(changes)
    return value


class DecideTests(unittest.TestCase):
    def check(self, value, kind, exit=None, **fields):
        action = decide(copy.deepcopy(value))
        self.assertEqual(action["kind"], kind, action)
        if exit is not None:
            self.assertEqual(action["exit"], exit, action)
        for key, expected in fields.items():
            self.assertEqual(action.get(key), expected, action)
        return action

    def test_guards(self):
        manual = snapshot({})
        manual["round"]["version"] = 1
        two_open = snapshot({}, rounds={"open": ["R1", "R2"], "closed": [], "ids": ["R1", "R2"]})
        halted = snapshot(
            {"A1": assignment()}, halts=[{"id": "H1", "cleared_utc": None, "code": "lost"}]
        )
        cleared = snapshot(
            {"A1": assignment()}, halts=[{"id": "H1", "cleared_utc": utc(-5), "code": "lost"}]
        )
        cases = [
            ("manual v1 round", manual, "Park", 0, {"reason": "manual-round"}),
            ("two open rounds", two_open, "Stop", 10, {"reason": "multiple-open-rounds"}),
            ("uncleared halt", halted, "Park", 10, {"reason": "halted"}),
            ("cleared halt", cleared, "LaunchExecutor", 0, {}),
            (
                "dirty checkout",
                snapshot({"A1": assignment()}, checkout={"clean": False, "head_on_default": True}),
                "Stop", 10, {"reason": "dirty-checkout"},
            ),
            (
                "diverged checkout",
                snapshot(checkout={"clean": True, "head_on_default": False}),
                "Stop", 10, {"reason": "diverged-checkout"},
            ),
            (
                "remote object missing",
                snapshot(checkout={"clean": True, "head_on_default": None}),
                "Fetch", 0, {},
            ),
            (
                "remote unknown",
                snapshot(remote={"default_sha": None, "unknown": "ls-remote failed"}),
                "Unknown", 11, {},
            ),
        ]
        for name, value, kind, exit, fields in cases:
            with self.subTest(name):
                self.check(value, kind, exit, **fields)

    def test_session_recovery(self):
        def with_session(record, process):
            return snapshot(
                {"A1": assignment()},
                sessions={"S1": record},
                processes={"S1": process} if process is not None else {},
            )

        alive = {"pid": 42, "alive": True, "exit": None}
        dead = {"pid": 42, "alive": False, "exit": None}
        exited = {"pid": 42, "alive": False, "exit": {"code": 0}}
        cases = [
            ("launching with process", session("executor", "launching"), alive, "AckSession"),
            ("launching within grace", session("executor", "launching"), {"pid": None, "alive": False, "exit": None}, "Wait"),
            ("launching past grace", session("executor", "launching", started=-600), None, "MarkLost"),
            ("running and alive", session("executor"), alive, "Wait"),
            ("running but dead", session("executor"), dead, "MarkLost"),
            ("past deadline", session("executor", deadline=-1), alive, "KillSession"),
            ("exited not ended", session("executor"), exited, "ImportSession"),
            ("exited while launching", session("executor", "launching"), exited, "ImportSession"),
            ("merger in flight", session("merger"), None, "VerifyMerge"),
        ]
        for name, record, process, kind in cases:
            with self.subTest(name):
                self.check(with_session(record, process), kind, session="S1" if kind != "Wait" else None)

    def test_containment_still_runs_while_halted(self):
        halts = [{"id": "H1", "cleared_utc": None, "code": "x"}]
        value = snapshot(
            {"A1": assignment()},
            sessions={"S1": session("executor", deadline=-1)},
            processes={"S1": {"pid": 42, "alive": True, "exit": None}},
            halts=halts,
        )
        self.check(value, "KillSession", session="S1")
        value["processes"]["S1"]["exit"] = {"code": 0}
        value["round"]["sessions"]["S1"]["deadline_utc"] = utc(60)
        self.check(value, "Park", 10, reason="halted")

    def test_kill_before_import_across_sessions(self):
        value = snapshot(
            {"A1": assignment(), "A2": assignment(aid="A2")},
            sessions={
                "S1": session("executor"),
                "S2": session("executor", assignment="A2", deadline=-5),
            },
            processes={
                "S1": {"pid": 1, "alive": False, "exit": {"code": 0}},
                "S2": {"pid": 2, "alive": True, "exit": None},
            },
            limits={**snapshot()["limits"], "max_parallel": 2},
        )
        self.check(value, "KillSession", session="S2")

    def test_no_open_round(self):
        def closed(*deltas):
            ids = [f"R{n}" for n in range(1, len(deltas) + 1)]
            return {
                "open": [],
                "closed": [{"id": i, "delta": d} for i, d in zip(ids, deltas)],
                "ids": ids,
            }

        cases = [
            ("L1 parks", snapshot(), "Park", 0, {"reason": "no-round"}),
            ("--new-round starts", snapshot(new_round=True), "InitRound", 0, {"round_id": "R1", "base": REMOTE}),
            ("L3 starts", snapshot(autonomy=3, rounds=closed("changed")), "InitRound", 0, {"round_id": "R2"}),
            ("stall", snapshot(autonomy=3, rounds=closed("changed", "none", "none")), "Park", 10, {"reason": "stalled"}),
            ("one none is not a stall", snapshot(autonomy=3, rounds=closed("none")), "InitRound", 0, {}),
            ("max rounds", snapshot(autonomy=3, rounds_this_run=1), "Park", 0, {"reason": "max-rounds"}),
        ]
        for name, value, kind, exit, fields in cases:
            with self.subTest(name):
                self.check(value, kind, exit, **fields)

    def test_planning(self):
        planner_live = snapshot(
            {}, sessions={"S1": session("planner")},
            processes={"S1": {"pid": 42, "alive": True, "exit": None}},
        )
        planner_done = snapshot({}, sessions={"S1": session("planner", "exited")})
        cases = [
            ("launch planner", snapshot({}), "LaunchPlanner", 0, {}),
            ("planner running", planner_live, "Wait", 0, {}),
            ("planner produced nothing", planner_done, "Hold", 10, {}),
        ]
        for name, value, kind, exit, fields in cases:
            with self.subTest(name):
                self.check(value, kind, exit, **fields)

    def test_assignment_table(self):
        def one(a, **changes):
            return snapshot({"A1": a}, **{"prs": {"A1": {"pr": open_pr()}}, **changes})

        exhausted = assignment("result-ready", results=3, reviews=[("needs-fix", HEAD)])
        cases = [
            ("assigned", one(assignment()), "LaunchExecutor", {"repair": False}),
            ("blocked result", one(assignment("blocked", results=1)), "Hold", {}),
            ("needs review", one(assignment("result-ready", results=1)), "LaunchReviewer", {"head": HEAD}),
            (
                "needs fix",
                one(assignment("result-ready", results=1, reviews=[("needs-fix", HEAD)])),
                "LaunchExecutor", {"repair": True},
            ),
            ("repairs exhausted", one(exhausted), "Hold", {}),
            (
                "review blocked",
                one(assignment("result-ready", results=1, reviews=[("blocked", HEAD)])),
                "Hold", {},
            ),
            (
                "ready at L1",
                one(assignment("result-ready", results=1, reviews=[("ready", HEAD)])),
                "Park", {"reason": "awaiting-merge", "exit": 0},
            ),
            (
                "PR missing",
                one(assignment("result-ready", results=1), prs={"A1": {"pr": None}}),
                "Hold", {},
            ),
            (
                "PR closed",
                one(assignment("result-ready", results=1), prs={"A1": {"pr": open_pr(state="CLOSED")}}),
                "Hold", {},
            ),
            (
                "merged externally",
                one(assignment("result-ready", results=1), prs={"A1": {"pr": open_pr(state="MERGED")}}),
                "Hold", {},
            ),
            (
                "head moved",
                one(assignment("result-ready", results=1), prs={"A1": {"pr": open_pr(HEAD2)}}),
                "Hold", {},
            ),
            (
                "PR unknown",
                one(assignment("result-ready", results=1), prs={"A1": {"unknown": "gh failed"}}),
                "Unknown", {"exit": 11},
            ),
            ("terminal with worktree", one(assignment("merged", results=1), worktrees={"A1": {"exists": True, "dirty": False}}), "Cleanup", {}),
            ("terminal dirty worktree", one(assignment("cancelled"), worktrees={"A1": {"exists": True, "dirty": True}}), "Hold", {}),
        ]
        for name, value, kind, fields in cases:
            with self.subTest(name):
                self.check(value, kind, **fields)

    def test_holds_name_the_assignment_and_reason(self):
        value = snapshot({"A1": assignment("blocked", results=1)})
        action = self.check(value, "Hold", 10)
        self.assertEqual(action["holds"], [{"assignment": "A1", "reason": "result-blocked"}])

    def test_merge_gate_wiring(self):
        self.check(ready_for_merge(), "Merge", 0, assignment="A1", head=HEAD)
        self.check(ready_for_merge(checks={"A1": {"state": "pending"}}), "Wait", 0)
        self.check(ready_for_merge(checks={"A1": {"state": "failed"}}), "Hold", 10)
        self.check(ready_for_merge(checks={"A1": {"unknown": "api"}}), "Unknown", 11)
        value = ready_for_merge(checks={"A1": {"state": "pending"}})
        value["round"]["assignments"]["A1"]["reviews"][0]["utc"] = utc(-3601 - 60 * 60)
        self.check(value, "Hold", 10)
        self.check(ready_for_merge(diffs={"A1": {"files": ["src/x.py"], "changed_lines": 1}}), "Hold")

    def test_old_head_review_is_ignored(self):
        value = snapshot(
            {"A1": assignment("result-ready", results=2)},
            prs={"A1": {"pr": open_pr()}},
        )
        value["round"]["assignments"]["A1"]["reviews"] = [
            {"result": "results/A1-1.json", "head_sha": HEAD2, "verdict": "ready", "utc": utc(-60)}
        ]
        self.check(value, "LaunchReviewer")

    def test_priority_and_parallelism(self):
        assignments = {
            "A1": assignment(),
            "A2": assignment("result-ready", results=1, aid="A2"),
            "A3": assignment("merged", results=1, aid="A3"),
        }
        prs = {"A2": {"pr": open_pr(headRefName="task/a2")}}
        worktrees = {"A3": {"exists": True, "dirty": False}}
        value = snapshot(assignments, prs=prs, worktrees=worktrees)
        self.check(value, "LaunchReviewer", assignment="A2")
        value["round"]["sessions"] = {"S1": session("reviewer", assignment="A2")}
        value["processes"] = {"S1": {"pid": 1, "alive": True, "exit": None}}
        self.check(value, "Cleanup", assignment="A3")
        value["limits"]["max_parallel"] = 2
        self.check(value, "LaunchExecutor", assignment="A1")

    def test_hold_on_one_assignment_does_not_block_another(self):
        value = snapshot(
            {"A1": assignment("blocked", results=1), "A2": assignment(aid="A2")}
        )
        action = self.check(value, "LaunchExecutor", assignment="A2")
        self.assertEqual(action["holds"][0]["assignment"], "A1")

    def test_session_budget_parks(self):
        sessions = {f"S{n}": session("executor", "exited", assignment="A9") for n in range(1, 9)}
        self.check(snapshot({"A1": assignment()}, sessions=sessions), "Park", 10, reason="budget")

    def test_round_end(self):
        merged = assignment("merged", results=1)
        reconcile = assignment("merged", kind="reconcile", results=1, aid="A2")
        cases = [
            ("L1 awaits reconcile", snapshot({"A1": merged}), "Park", {"reason": "awaiting-reconcile"}),
            ("L3 creates reconcile", snapshot({"A1": merged}, autonomy=3), "CreateReconcile", {"start": REMOTE}),
            ("all cancelled still reconciles", snapshot({"A1": assignment("cancelled")}, autonomy=3), "CreateReconcile", {}),
            ("final gate", snapshot({"A1": merged, "A2": reconcile}, autonomy=3), "RunFinalGate", {}),
            ("close", snapshot({"A1": merged, "A2": reconcile}, autonomy=3, final_gate="passed"), "CloseRound", {}),
            ("red gate", snapshot({"A1": merged, "A2": reconcile}, autonomy=3, final_gate="failed"), "Hold", {}),
            (
                "cancelled reconcile",
                snapshot({"A1": merged, "A2": assignment("cancelled", kind="reconcile", aid="A2")}, autonomy=3),
                "Hold", {},
            ),
        ]
        for name, value, kind, fields in cases:
            with self.subTest(name):
                self.check(value, kind, **fields)

    def test_decide_does_not_mutate_its_input(self):
        value = ready_for_merge()
        before = copy.deepcopy(value)
        decide(value)
        self.assertEqual(value, before)


if __name__ == "__main__":
    unittest.main()
