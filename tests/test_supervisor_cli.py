"""End-to-end checks of the read-only supervisor CLI against real Git and a fake gh."""

import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPERVISE = ROOT / "scripts" / "supervise.py"
ROUND = ROOT / "scripts" / "round.py"
FAKES = ROOT / "tests" / "fakes"
POLICY = "[supervisor]\nautonomy = 1\n[policy.merge]\nrequired_checks = ['check']\n"


class SupervisorCliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.origin = self.tmp / "origin.git"
        self.repo = self.tmp / "project"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        subprocess.run(["git", "clone", "-q", self.origin, self.repo], check=True,
                       capture_output=True)
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / ".gitignore").write_text(".agent-runs/\nHANDOFF.md\n")
        (self.repo / ".agent").mkdir()
        (self.repo / ".agent/supervisor.toml").write_text(POLICY)
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.git("push", "-q", "origin", "main")
        self.base = self.git("rev-parse", "HEAD")
        self.state = self.tmp / "gh-state.json"
        self.log = self.tmp / "gh-log.jsonl"
        self.gh_state({})

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args],
            text=True, capture_output=True, check=True,
        ).stdout.strip()

    def gh_state(self, value):
        self.state.write_text(json.dumps(value))

    def gh_calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def env(self):
        return {
            **os.environ,
            "PATH": f"{FAKES}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_STATE": str(self.state),
            "FAKE_GH_LOG": str(self.log),
        }

    def supervise(self, *args, code=0):
        done = subprocess.run(
            [sys.executable, str(SUPERVISE), "--repo", str(self.repo), *args],
            text=True, capture_output=True, env=self.env(), check=False,
        )
        self.assertEqual(done.returncode, code, done.stdout + done.stderr)
        return done

    def next_action(self, *args, code=0):
        return json.loads(self.supervise("next", *args, code=code).stdout)

    def ledger(self, *args):
        done = subprocess.run(
            [sys.executable, str(ROUND), "--repo", str(self.repo), *args],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def start_round(self):
        spec = self.repo / ".agent-runs" / "spec.md"
        spec.parent.mkdir(exist_ok=True)
        spec.write_text("Document the behavior.\n")
        self.ledger("init", "R1", "--base", "main", "--supervised")
        self.ledger("assign", "R1", "A1", "--item", "TASK-1", "--branch", "task/a1",
                    "--spec", str(spec), "--owns", "docs/**")

    def submit_result(self):
        self.git("switch", "-q", "-c", "task/a1")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/a.md").write_text("Behavior\n")
        self.git("add", "docs/a.md")
        self.git("commit", "-qm", "docs")
        head = self.git("rev-parse", "HEAD")
        self.git("push", "-q", "origin", "task/a1")
        self.git("switch", "-q", "main")
        manifest = json.loads(self.ledger("status", "R1"))
        result = self.repo / ".agent-runs" / "result.json"
        result.write_text(json.dumps({
            "assignment": "A1",
            "base_sha": self.base,
            "packet_sha256": manifest["assignments"]["A1"]["packet_sha256"],
            "head_sha": head,
            "pr": "https://example.invalid/pull/1",
            "checks": [{"command": ["true"], "status": "passed", "evidence": "ok"}],
        }))
        self.ledger("record", "R1", "--result", str(result))
        return head

    def pr(self, head, **changes):
        return {
            "number": 1, "state": "OPEN", "isDraft": False, "headRefOid": head,
            "headRefName": "task/a1", "baseRefName": "main", "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN", "url": "https://example.invalid/pull/1", **changes,
        }

    def test_no_round_parks_at_l1_and_new_round_proposes_init(self):
        self.assertEqual(self.next_action()["reason"], "no-round")
        action = self.next_action("--new-round")
        self.assertEqual(action, {"kind": "InitRound", "exit": 0, "round_id": "R1", "base": self.base})
        self.assertFalse((self.repo / ".agent-runs").exists())

    def test_result_flow_reads_pr_state_and_never_writes(self):
        self.start_round()
        self.assertEqual(self.next_action()["kind"], "LaunchExecutor")
        head = self.submit_result()
        self.gh_state({"prs": {"task/a1": [self.pr(head)]}})
        before = self.ledger("status", "R1")
        self.assertEqual(self.next_action(), {
            "kind": "LaunchReviewer", "exit": 0, "assignment": "A1", "head": head
        })
        self.ledger("review", "R1", "A1", "--head", head, "--verdict", "ready",
                    "--evidence", "manual", "--reviewer", "operator")
        self.assertEqual(self.next_action()["reason"], "awaiting-merge")
        self.gh_state({"prs": {"task/a1": [self.pr("f" * 40)]}})
        held = self.next_action(code=10)
        self.assertEqual(held["holds"], [{"assignment": "A1", "reason": "head-moved"}])
        self.assertEqual(json.loads(self.ledger("status", "R1"))["assignments"]["A1"]["state"],
                         json.loads(before)["assignments"]["A1"]["state"])
        for call in self.gh_calls():
            self.assertIn(call[:2], (["pr", "list"], ["api", "--paginate"]), call)

    def test_l2_gate_reads_required_checks_on_the_exact_head(self):
        (self.repo / ".agent/supervisor.toml").write_text(
            POLICY.replace("autonomy = 1", "autonomy = 2") + "auto_merge = true\n"
        )
        self.git("commit", "-qam", "grant L2")
        self.git("push", "-q", "origin", "main")
        self.base = self.git("rev-parse", "HEAD")
        self.start_round()
        head = self.submit_result()
        self.ledger("review", "R1", "A1", "--head", head, "--verdict", "ready",
                    "--evidence", "manual", "--reviewer", "operator")
        run = {"name": "check", "status": "completed", "conclusion": "success", "id": 5}
        self.gh_state({"prs": {"task/a1": [self.pr(head)]}, "check_runs": {head: [run]}})
        self.assertEqual(self.next_action(), {"kind": "Merge", "exit": 0, "assignment": "A1", "head": head})
        self.assertIn(f"repos/{{owner}}/{{repo}}/commits/{head}/check-runs", sum(self.gh_calls(), []))
        self.gh_state({"prs": {"task/a1": [self.pr(head)]}})
        self.assertEqual(self.next_action(code=10)["holds"][0]["reason"], "checks-failed")
        self.gh_state({"prs": {"task/a1": [self.pr(head)]}, "fail": ["check-runs"]})
        self.assertEqual(self.next_action(code=11)["kind"], "Unknown")

    def test_gh_failure_is_unknown_not_success(self):
        self.start_round()
        self.submit_result()
        self.gh_state({"fail": ["pr list"]})
        action = self.next_action(code=11)
        self.assertEqual(action["kind"], "Unknown")

    def test_dirty_or_diverged_checkout_stops(self):
        (self.repo / "README.md").write_text("dirty\n")
        self.assertEqual(self.next_action(code=10)["reason"], "dirty-checkout")
        self.git("add", "README.md")
        self.git("commit", "-qm", "local only")
        self.assertEqual(self.next_action(code=10)["reason"], "diverged-checkout")

    def test_unfetched_remote_head_asks_for_fetch(self):
        other = self.tmp / "other"
        subprocess.run(["git", "clone", "-q", self.origin, other], check=True, capture_output=True)
        (other / "x").write_text("x\n")
        self.git("add", "x", cwd=other)
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "x", cwd=other)
        self.git("push", "-q", "origin", "main", cwd=other)
        self.assertEqual(self.next_action()["kind"], "Fetch")

    def test_session_processes_are_observed_by_uuid(self):
        self.start_round()
        session_uuid = str(uuid.uuid4())
        deadline = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.ledger("session", "start", "R1", "--role", "executor", "--assignment", "A1",
                    "--runner", "claude", "--session-uuid", session_uuid, "--cwd", str(self.tmp),
                    "--deadline", deadline)
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)", session_uuid]
        )
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        sessions = self.repo / ".agent-runs/supervisor/sessions"
        sessions.mkdir(parents=True)
        (sessions / f"{session_uuid}.pid").write_text(f"{child.pid}\n")
        self.assertEqual(self.next_action(), {"kind": "AckSession", "exit": 0, "session": "S1", "pid": child.pid})
        self.ledger("session", "ack", "R1", "S1", "--pid", str(os.getpid()))
        self.assertEqual(self.next_action()["kind"], "MarkLost")
        (sessions / f"{session_uuid}.exit.json").write_text('{"code": 0}\n')
        self.assertEqual(self.next_action()["kind"], "ImportSession")

    def test_halt_parks_with_attention(self):
        self.start_round()
        self.ledger("halt", "R1", "--code", "test", "--detail", "inspect", "--action", "look")
        self.assertEqual(self.next_action(code=10), {
            "kind": "Park", "exit": 10, "reason": "halted", "halts": ["H1"]
        })

    def test_status_explains_the_round(self):
        self.start_round()
        out = self.supervise("status").stdout
        self.assertIn("Open round: R1 v2", out)
        self.assertIn("A1 assigned task/a1", out)
        self.assertIn("Next: LaunchExecutor", out)

    def test_configuration_errors_exit_2(self):
        (self.repo / ".agent/supervisor.toml").write_text("[supervisor]\nautonomy = 2\n")
        self.git("commit", "-qam", "unsafe")
        self.git("push", "-q", "origin", "main")
        done = self.supervise("next", code=2)
        self.assertIn("auto_merge", done.stderr)
        self.supervise("--autonomy", "1", "next", code=2)

    def test_run_is_dry_only_logged_and_single_instance(self):
        self.supervise("run", "--once", code=2)
        done = self.supervise("run", "--dry-run", "--once")
        self.assertEqual(json.loads(done.stdout)["reason"], "no-round")
        state = self.repo / ".agent-runs/supervisor"
        entries = [json.loads(line) for line in (state / "log.jsonl").read_text().splitlines()]
        self.assertEqual(entries[-1]["action"]["reason"], "no-round")
        self.assertTrue(entries[-1]["dry_run"])
        self.assertEqual(json.loads((state / "last.json").read_text())["action"]["kind"], "Park")
        with (state / "lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.supervise("run", "--dry-run", "--once", code=3)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_effectful_decision_ends_a_dry_run(self):
        self.start_round()
        done = self.supervise("run", "--dry-run")
        self.assertEqual(json.loads(done.stdout)["kind"], "LaunchExecutor")


if __name__ == "__main__":
    unittest.main()
