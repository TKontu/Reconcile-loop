"""The optional round supervisor: completion, carry-safe recycling and the no-endless-wait bound."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "round_supervisor", ROOT / "scripts" / "round_supervisor.py"
)
rs = importlib.util.module_from_spec(_spec)
sys.modules["round_supervisor"] = rs  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(rs)

CFG = rs.Config()
T0 = 1_000_000.0


def tracker(**kw):
    return rs.Tracker(**{"round": 4, "started": T0, "last_progress": T0, **kw})


def obs(after, **kw):
    base = {"now": T0 + after, "status": "idle", "sentinel": None, "activity": T0 + after}
    return rs.Observation(**{**base, **kw})


class FakeHerdr(rs.Herdr):
    """Records which tab is closed; the agent list is scripted."""

    def __init__(self, agents):
        super().__init__(lambda _cmd, _t: (0, "{}"))
        self.listed = agents
        self.closed = []

    def agents(self):
        return self.listed

    def close_tab(self, tab):
        self.closed.append(tab)


class PolicyTests(unittest.TestCase):
    def test_idle_without_sentinel_is_not_completion(self):
        self.assertEqual(rs.decide(CFG, tracker(), obs(60, status="idle")).kind, "wait")

    def test_sentinel_completes_the_round_once_settled(self):
        done = {"outcome": "continue"}
        self.assertEqual(rs.decide(CFG, tracker(), obs(60, sentinel=done)).kind, "next")
        t = tracker()
        self.assertEqual(
            rs.decide(CFG, t, obs(60, sentinel=done, status="working")).kind, "wait"
        )
        late = obs(60 + CFG.settle_s, sentinel=done, status="working")
        self.assertEqual(rs.decide(CFG, t, late).kind, "next")

    def test_requested_halts_win_over_the_next_round(self):
        halt = obs(1, sentinel={"outcome": "halt"})
        self.assertEqual(rs.decide(CFG, tracker(), halt).kind, "halt")
        after = obs(1, sentinel={"outcome": "continue"}, stop_after_round=True)
        self.assertEqual(rs.decide(CFG, tracker(), after).kind, "halt")
        self.assertEqual(rs.decide(CFG, tracker(), obs(1, stop_now=True)).kind, "halt")
        self.assertEqual(rs.decide(CFG, tracker(), obs(1, stop_after_round=True)).kind, "wait")

    def test_silence_nudges_after_the_threshold_only(self):
        quiet = obs(CFG.silence_s - 1, activity=T0)
        self.assertEqual(rs.decide(CFG, tracker(), quiet).kind, "wait")
        silent = obs(CFG.silence_s, activity=T0)
        self.assertEqual(rs.decide(CFG, tracker(), silent).kind, "nudge_silent")

    def test_a_heartbeating_session_with_no_outward_progress_still_terminates(self):
        """Transcript writes alone must not extend the round forever."""
        t, kinds, elapsed = tracker(), [], 0
        while elapsed < CFG.round_cap_s and "recycle" not in kinds:
            elapsed += CFG.poll_s
            action = rs.decide(CFG, t, obs(elapsed))  # activity is always "just now"
            kinds.append(action.kind)
            if action.kind.startswith("nudge"):
                t.nudges += 1
                t.last_nudge = T0 + elapsed
        self.assertEqual(kinds.count("nudge_progress"), CFG.max_nudges)
        self.assertEqual(kinds[-1], "recycle")

    def test_round_cap_recycles_a_busy_round(self):
        t = tracker(last_progress=T0 + CFG.round_cap_s)
        self.assertEqual(rs.decide(CFG, t, obs(CFG.round_cap_s)).kind, "recycle")

    def test_vanished_agent_recycles(self):
        self.assertEqual(rs.decide(CFG, tracker(), obs(5, status=None)).kind, "recycle")

    def test_an_unanswered_dialog_is_refused_never_approved(self):
        t = tracker()
        self.assertEqual(rs.decide(CFG, t, obs(10, status="blocked")).kind, "wait")
        late = obs(10 + CFG.blocked_s, status="blocked")
        self.assertEqual(rs.decide(CFG, t, late).kind, "deny")

    def test_usage_limit_waits_without_nudging_but_only_for_a_bounded_time(self):
        t = tracker()
        limited = obs(CFG.silence_s, activity=T0, limited=True)
        self.assertEqual(rs.decide(CFG, t, limited).reason, "usage limit")
        self.assertEqual(t.nudges, 0)
        late = obs(CFG.silence_s + CFG.limit_max_s, activity=T0, limited=True)
        self.assertNotEqual(rs.decide(CFG, t, late).reason, "usage limit")

    def test_breaker_halts_on_repeated_recycles_and_on_a_frozen_main(self):
        t = tracker(main_at_start="a")
        self.assertIsNone(rs.after_round(CFG, t, recycled=True, main_sha="b"))
        stop = rs.after_round(CFG, t, recycled=True, main_sha="c")
        self.assertEqual(stop.kind, "halt")
        t = tracker(main_at_start="a")
        self.assertIsNone(rs.after_round(CFG, t, recycled=False, main_sha="a"))
        self.assertIsNone(rs.after_round(CFG, t, recycled=False, main_sha="a"))
        self.assertIsNotNone(rs.after_round(CFG, t, recycled=False, main_sha="a"))
        t = tracker(main_at_start="a", recycles=1, no_advance=2)
        self.assertIsNone(rs.after_round(CFG, t, recycled=False, main_sha="b"))
        self.assertEqual((t.recycles, t.no_advance), (0, 0))

    def test_overrides_shorten_timers_and_reject_unknown_keys(self):
        self.assertEqual(rs.with_overrides(CFG, ["silence_s=60"]).silence_s, 60)
        with self.assertRaises(TypeError):
            rs.with_overrides(CFG, ["nope=1"])

    def test_phase_shows_a_dead_supervisor_and_a_halt(self):
        self.assertEqual(
            rs.phase_of(halt=None, alive=False, stopping=False)[0], "SUPERVISOR DOWN"
        )
        self.assertEqual(
            rs.phase_of(halt={"reason": "r"}, alive=False, stopping=False), ("HALTED", "r")
        )
        self.assertEqual(rs.phase_of(halt=None, alive=True, stopping=True)[0], "STOPPING")


class StateTests(unittest.TestCase):
    """Tests that touch the supervisor's state directory, redirected to a temp dir."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        for name in ("STATE", "ROOT"):
            patcher = mock.patch.object(rs, name, self.tmp)
            patcher.start()
            self.addCleanup(patcher.stop)

    def open_round(self, started):
        (self.tmp / "current.json").write_text(json.dumps({"round": 7, "started": started}))

    def test_failed_probe_counts_as_no_change(self):
        self.assertIsNone(rs.fingerprint(lambda _cmd, _t: (1, "")))

    def test_a_round_ledger_write_counts_as_outward_progress(self):
        ledger = self.tmp / ".agent-runs" / "R1" / "round.json"
        ledger.parent.mkdir(parents=True)
        ledger.write_text("{}")
        probe = lambda _cmd, _t: (0, "abc\trefs/heads/main")  # noqa: E731
        before = rs.fingerprint(probe)
        os.utime(ledger, ns=(1, 1))
        self.assertNotEqual(rs.fingerprint(probe), before)

    def test_main_is_probed_on_the_configured_branch(self):
        calls = []
        rs.main_sha(lambda cmd, _t: calls.append(list(cmd)) or (0, "abc\tref"))
        self.assertEqual(calls[0][-1], f"refs/heads/{rs.BRANCH}")
        (self.tmp / ".agent").mkdir()
        (self.tmp / ".agent/config.toml").write_text(
            '[project]\ndefault_branch = "trunk"\n[supervisor]\npermission_mode = "default"\n'
        )
        config = rs.project_config(self.tmp)
        self.assertEqual(config["project"]["default_branch"], "trunk")
        self.assertEqual(config["supervisor"]["permission_mode"], "default")
        self.assertEqual(rs.project_config(self.tmp / "missing"), {})

    def test_a_note_must_be_a_tldr_and_open_items_need_a_ref(self):
        self.assertEqual(rs.note("result", "x" * (rs.NOTE_MAX + 1), "", ""), 2)
        self.assertEqual(rs.note("open", "needs a ruling", "", ""), 2)
        self.assertEqual(rs.read_news(), [])

    def test_owed_items_stay_listed_until_closed(self):
        self.assertEqual(rs.note("open", "Rule on TASK-1", "TASK-1", ""), 0)
        self.assertEqual(rs.note("open", "Rule on TASK-2", "TASK-2", ""), 0)
        self.assertEqual(rs.note(None, "", "", "TASK-1"), 0)
        self.assertEqual([i["ref"] for i in rs.open_items(rs.read_news())], ["TASK-2"])

    def test_deadline_requests_a_stop_only_once_reached(self):
        self.assertFalse(rs.stop_requested())
        rs.set_deadline("1h30m")
        self.assertFalse(rs.stop_requested(rs.time.time() + 5000))
        self.assertTrue(rs.stop_requested(rs.time.time() + 5500))
        with self.assertRaises(ValueError):
            rs.parse_duration("soon")

    def test_preflight_refuses_without_its_own_workspace(self):
        sup = rs.Supervisor(CFG, (), FakeHerdr([]))
        with mock.patch.dict(os.environ, {"HERDR_ENV": "1", "HERDR_WORKSPACE_ID": ""}):
            with self.assertRaises(SystemExit):
                sup.preflight(allow_other=False)

    def test_preflight_refuses_another_working_session(self):
        env = {"HERDR_ENV": "1", "HERDR_PANE_ID": "me", "HERDR_WORKSPACE_ID": "w1"}
        other = {"agent": "claude", "cwd": str(rs.ROOT), "pane_id": "p1", "agent_status": "working"}
        sup = rs.Supervisor(CFG, (), FakeHerdr([other]))
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(SystemExit):
                sup.preflight(allow_other=False)
            sup.preflight(allow_other=True)

    def test_complete_requires_a_handoff_from_this_round(self):
        self.open_round(2_000_000_000.0)  # after any file written now
        (self.tmp / "HANDOFF.md").write_text("x")
        self.assertEqual(rs.complete("continue", "", lambda _c, _t: (0, "")), 1)
        self.assertFalse((self.tmp / "complete.json").exists())

    def test_complete_validates_with_round_py_and_records_the_round(self):
        self.open_round(1.0)
        (self.tmp / "HANDOFF.md").write_text("x")
        calls = []
        self.assertEqual(rs.complete("continue", "", lambda _c, _t: (1, "bad")), 1)
        ok = lambda cmd, _t: calls.append(list(cmd)) or (0, "")  # noqa: E731
        self.assertEqual(rs.complete("continue", "", ok), 0)
        self.assertEqual(Path(calls[0][1]).name, "round.py")
        self.assertEqual(calls[0][2], "check-handoff")
        sentinel = rs.read_sentinel(7)
        self.assertEqual(sentinel["outcome"], "continue")
        self.assertIsNone(rs.read_sentinel(8))

    def test_the_real_round_py_rejects_the_unfilled_template(self):
        self.open_round(1.0)
        (self.tmp / "HANDOFF.md").write_text((ROOT / "templates/handoff.md").read_text())
        self.assertEqual(rs.complete("continue", ""), 1)


class HerdrTests(unittest.TestCase):
    def test_ending_a_round_closes_only_its_own_tab(self):
        herdr = FakeHerdr([{"name": rs.LANE_PREFIX + "task1", "agent": "claude", "tab_id": "t11"}])
        sup = rs.Supervisor(CFG, (), herdr)
        sup.tab = "t99"
        with mock.patch.object(rs.time, "sleep", lambda _s: None):
            sup.end_session()
        self.assertEqual(herdr.closed, ["t99"])

    def test_supervised_sessions_get_the_permission_mode_then_extra_args(self):
        calls = []

        def record(cmd, _timeout):
            calls.append(list(cmd))
            return 0, '{"result": {}}'

        sup = rs.Supervisor(CFG, ("--verbose",), rs.Herdr(record))
        sup.herdr.start("p9", "uuid", 1, sup.extra)
        self.assertEqual(calls[0][-3:], [*rs.PERMISSION_ARGS, "--verbose"])

    def test_the_orchestrator_tab_inherits_the_supervised_root(self):
        calls = []

        def record(cmd, _timeout):
            calls.append(list(cmd))
            return 0, '{"result": {"tab": {"tab_id": "t"}, "root_pane": {"pane_id": "p"}}}'

        self.assertEqual(rs.Herdr(record).new_tab(), ("t", "p"))
        self.assertIn(f"ROUND_SUPERVISOR_ROOT={rs.ROOT}", calls[0])


class RepoNameTests(unittest.TestCase):
    """Herdr names are global, so two repos' loops must never share one."""

    def test_names_carry_the_repo_slug(self):
        names = rs.repo_names(Path("/work/My Repo.v2"), {})
        self.assertEqual(names["slug"], "my-repo-v2")
        self.assertEqual(names["agent"], "round-planner-my-repo-v2")
        self.assertEqual(names["loop_tab"], "round-loop-my-repo-v2")
        self.assertEqual(names["lane_prefix"], "live-my-repo-v2-")

    def test_config_name_overrides_the_directory(self):
        names = rs.repo_names(Path("/work/checkout"), {"supervisor": {"name": "Alpha"}})
        self.assertEqual(names["agent"], "round-planner-alpha")

    def test_two_repos_get_distinct_names(self):
        a, b = (rs.repo_names(Path(f"/work/{n}"), {}) for n in ("alpha", "beta"))
        self.assertTrue(all(a[k] != b[k] for k in ("agent", "loop_tab", "lane_prefix")))

    def test_dashboard_lists_only_this_repos_lanes(self):
        mine = {"name": rs.LANE_PREFIX + "task1", "agent_status": "working"}
        other = {"name": "live-otherrepo-task1", "agent_status": "working"}
        view = rs.gather_view(FakeHerdr([mine, other]))
        self.assertEqual(view["lanes"], [(mine["name"], "working")])

    def test_dashboard_prefers_lane_records_over_agent_state(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        lane = Path(tmp.name) / ".agent-runs" / "lanes" / "sweep"
        lane.mkdir(parents=True)
        (lane / "runner.rc").write_text("0\n")
        record = {"lane": "sweep", "label": rs.LANE_PREFIX + "sweep", "rc_file": str(lane / "runner.rc")}
        (lane / "lane.json").write_text(json.dumps(record))
        idle = {"name": rs.LANE_PREFIX + "sweep", "agent_status": "idle"}
        with mock.patch.object(rs, "ROOT", Path(tmp.name)):
            view = rs.gather_view(FakeHerdr([idle]))
        self.assertEqual(view["lanes"], [(rs.LANE_PREFIX + "sweep", "done")])
        self.assertEqual(view["lanes_kind"], "(lane state)")

    def test_round_prompt_starts_probes_and_releases_lanes_with_the_helper(self):
        prompt = rs.ROUND_PROMPT.format(round=1, script="s", lane_prefix=rs.LANE_PREFIX, lanes="L")
        for step in ("L status", "L start <lane>", "L recorded <lane>", "L cleanup --go"):
            self.assertIn(step, prompt)
        self.assertTrue(rs.LANES.is_file())

    def test_round_prompt_names_lanes_with_the_repo_prefix(self):
        prompt = rs.ROUND_PROMPT.format(round=1, script="s", lane_prefix=rs.LANE_PREFIX, lanes="l")
        self.assertIn(rs.LANE_PREFIX + "<lane>", prompt)

    def test_never_adopts_another_checkouts_planner(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        state = Path(tmp.name)
        (state / "current.json").write_text(
            json.dumps({"round": 2, "session": "s", "tab": "t", "started": 1.0})
        )
        foreign = {"name": rs.AGENT, "cwd": "/somewhere/else"}
        with mock.patch.object(rs, "STATE", state):
            with self.assertRaises(SystemExit):
                rs.Supervisor(CFG, (), FakeHerdr([foreign])).adopt()
            own = {"name": rs.AGENT, "cwd": str(rs.ROOT)}
            self.assertTrue(rs.Supervisor(CFG, (), FakeHerdr([own])).adopt())


class WorkspaceTests(unittest.TestCase):
    """Tabs land in the supervisor's own workspace, never whichever one is focused."""

    def record(self):
        calls = []

        def run(cmd, _timeout):
            calls.append(list(cmd))
            return 0, json.dumps({"result": {
                "tab": {"tab_id": "t"}, "root_pane": {"pane_id": "p"}, "pane": {"pane_id": "q"},
            }})  # fmt: skip

        return calls, run

    def test_planner_tab_lands_in_the_supervisors_workspace(self):
        calls, run = self.record()
        with mock.patch.dict(os.environ, {"HERDR_WORKSPACE_ID": "w1D"}):
            rs.Herdr(run).new_tab()
        create = calls[0]
        self.assertEqual(create[:3], ["herdr", "tab", "create"])
        self.assertEqual(create[create.index("--workspace") + 1], "w1D")

    def test_up_opens_the_loop_tab_in_the_supervisors_workspace(self):
        calls, run = self.record()
        with mock.patch.dict(os.environ, {"HERDR_WORKSPACE_ID": "w1D"}), mock.patch.object(
            rs.time, "sleep", lambda _s: None
        ):
            rs.up([], rs.Herdr(run))
        create = next(c for c in calls if c[1:3] == ["tab", "create"])
        self.assertEqual(create[create.index("--workspace") + 1], "w1D")

    def test_round_prompt_forbids_lane_workspaces(self):
        prompt = rs.ROUND_PROMPT.format(round=1, script="s", lane_prefix=rs.LANE_PREFIX, lanes="l")
        self.assertIn("never create a Herdr workspace", prompt)


class DashboardTests(unittest.TestCase):
    @staticmethod
    def view(news):
        return {
            "now": T0, "phase": ("RUNNING", ""), "round": 3, "started": T0 - 600,
            "deadline": None, "lanes": [(rs.LANE_PREFIX + "task1", "idle")], "news": news,
        }  # fmt: skip

    def test_render_fits_the_screen_keeps_status_and_scrolls_the_news(self):
        news = [
            {"at": T0 - i, "round": 3, "kind": "result", "text": f"item {i}", "ref": ""}
            for i in reversed(range(50))  # the file is append-only, oldest first
        ]
        first = rs.render(self.view(news), 80, 24, 0)
        self.assertEqual(len(first), 24)
        self.assertIn("RUNNING", first[0])
        self.assertIn("item 0", "".join(first))
        scrolled = "".join(rs.render(self.view(news), 80, 24, 30))
        self.assertIn("RUNNING", scrolled)
        self.assertIn("item 30", scrolled)
        self.assertNotIn("item 0 ", scrolled)

    def test_stage_is_shown_in_the_header_not_the_feed(self):
        stage = {"at": T0, "round": 3, "kind": "stage", "text": "merge-round", "ref": ""}
        lines = rs.render(self.view([stage]), 80, 24, 0)
        self.assertIn("merge-round", lines[0])
        self.assertNotIn("merge-round", "".join(lines[1:]))


if __name__ == "__main__":
    unittest.main()
