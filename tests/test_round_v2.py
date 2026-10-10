"""Behavior checks for supervised (version 2) rounds on the autonomous branch."""

import fcntl
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "round.py"


class SupervisedRoundTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / ".gitignore").write_text(".agent-runs/\nHANDOFF.md\n")
        (self.repo / "README.md").write_text("Example\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.spec = self.repo / ".agent-runs" / "input.md"
        self.spec.parent.mkdir()
        self.spec.write_text("Document the approved behavior.\n")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], text=True
        ).strip()

    def cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def manifest(self):
        return json.loads((self.repo / ".agent-runs/R1/round.json").read_text())

    def assign(self, assignment="A1", *extra, ok=True, item=None, branch=None):
        return self.cli(
            "assign",
            "R1",
            assignment,
            "--item",
            item or f"TASK-{assignment}",
            "--branch",
            branch or f"task/{assignment.lower()}",
            "--spec",
            str(self.spec),
            *extra,
            ok=ok,
        )

    def start(self):
        self.cli("init", "R1", "--base", "main", "--supervised")
        self.assign("A1", "--owns", "docs/**")

    def submit(self, assignment="A1", head=None):
        data = {
            "assignment": assignment,
            "base_sha": self.base,
            "packet_sha256": self.manifest()["assignments"][assignment]["packet_sha256"],
            "head_sha": head or self.base,
            "pr": "https://example.invalid/pull/1",
            "checks": [
                {"command": ["git", "diff", "--check"], "status": "passed", "evidence": "ok"}
            ],
        }
        path = self.repo / ".agent-runs" / "result.json"
        path.write_text(json.dumps(data))
        self.cli("record", "R1", "--result", str(path))

    def review(self, verdict, head=None, ok=True):
        return self.cli(
            "review",
            "R1",
            "A1",
            "--head",
            head or self.base,
            "--verdict",
            verdict,
            "--evidence",
            "https://example.invalid/pull/1#verdict",
            "--reviewer",
            "operator",
            ok=ok,
        )

    def merge(self, ok=True):
        return self.cli(
            "resolve",
            "R1",
            "A1",
            "--outcome",
            "merged",
            "--head",
            self.base,
            "--merge",
            self.base,
            "--evidence",
            "Reviewed and merged",
            ok=ok,
        )

    def handoff(self):
        (self.repo / "HANDOFF.md").write_text(
            "# Handoff\nGenerated-UTC: 2026-10-10T10:00:00Z\n"
            f"Main-SHA: {self.base}\n\n"
            "## Round delta\nTASK-A1 reconciled.\n\n"
            "## Open work\nNone.\n\n"
            "## Next action\nPlan the next round.\n"
        )

    def close(self, *extra, ok=True):
        self.handoff()
        return self.cli(
            "close",
            "R1",
            "--main",
            "main",
            "--reconciliation",
            "README.md",
            "--handoff",
            "HANDOFF.md",
            "--evidence",
            "Final checks passed",
            *extra,
            ok=ok,
        )

    def test_default_init_stays_version_one_and_refuses_supervised_options(self):
        self.cli("init", "R1", "--base", "main")
        self.assertEqual(
            set(self.manifest()), {"version", "id", "base_sha", "state", "assignments"}
        )
        self.assertEqual(self.manifest()["version"], 1)
        self.assign("A1", "--owns", "docs/**", ok=False)
        self.assign("A1")
        packet = (self.repo / ".agent-runs/R1/prompts/A1.md").read_text()
        self.assertIn("Branch: task/a1\n\nUse an isolated checkout", packet)
        self.cli(
            "review", "R1", "A1", "--head", self.base, "--verdict", "ready",
            "--evidence", "x", "--reviewer", "operator", ok=False,
        )

    def test_supervised_init_writes_version_two_records(self):
        self.cli("init", "R1", "--base", "main", "--supervised")
        manifest = self.manifest()
        self.assertEqual(manifest["version"], 2)
        self.assertEqual(manifest["sessions"], {})
        self.assertEqual(manifest["halts"], [])
        self.cli("status", "R1")

    def test_supervised_assignment_binds_ownership_into_packet(self):
        self.cli("init", "R1", "--base", "main", "--supervised")
        self.assign("A1", ok=False)
        self.assign("A1", "--owns", "/etc/**", ok=False)
        self.assign(
            "A1", "--owns", "src/x/**", "--owns", "tests/test_x.py", "--resource", "db"
        )
        packet = (self.repo / ".agent-runs/R1/prompts/A1.md").read_text()
        self.assertIn("Kind: work\n", packet)
        self.assertIn("Owned-Path: src/x/**\nOwned-Path: tests/test_x.py\n", packet)
        self.assertIn("Resource: db\n", packet)
        record = self.manifest()["assignments"]["A1"]
        self.assertEqual(record["kind"], "work")
        self.assertEqual(record["owned_paths"], ["src/x/**", "tests/test_x.py"])
        self.assertEqual(record["resources"], ["db"])
        self.assertEqual(record["reviews"], [])

    def test_live_assignments_cannot_share_paths_or_resources(self):
        self.cli("init", "R1", "--base", "main", "--supervised")
        self.assign("A1", "--owns", "src/x/**", "--resource", "db")
        self.assign("A2", "--owns", "src/x/y.py", ok=False)
        self.assign("A2", "--owns", "src/**", ok=False)
        self.assign("A2", "--owns", "**", ok=False)
        self.assign("A2", "--owns", "docs/**", "--resource", "db", ok=False)
        self.assign("A2", "--owns", "docs/**", "--resource", "gpu")
        self.cli("resolve", "R1", "A1", "--outcome", "cancelled", "--evidence", "Stopped")
        self.assign("A3", "--owns", "src/x/**", "--resource", "db")

    def test_owned_paths_must_be_normalized_relative_paths(self):
        self.cli("init", "R1", "--base", "main", "--supervised")
        self.assign("A1", "--owns", "src/a")
        for pattern in ("./src/a", "src//a", "src/x/../a", "src/a/", "../outside", "src/./a", ""):
            with self.subTest(pattern=pattern):
                rejected = self.assign("A2", "--owns", pattern, ok=False)
                self.assertIn("--owns", rejected.stderr)
        self.assertEqual(list(self.manifest()["assignments"]), ["A1"])

    def test_reconcile_assignment_follows_terminal_work(self):
        self.start()
        self.assign("R", "--kind", "reconcile", "--owns", "backlog/**",
                    "--start", "main", ok=False)
        self.cli("resolve", "R1", "A1", "--outcome", "cancelled", "--evidence", "Stopped")
        self.assign("R", "--kind", "reconcile", "--owns", "backlog/**", ok=False)
        self.assign("A2", "--owns", "src/**", "--start", "main", ok=False)
        self.assign("R", "--kind", "reconcile", "--owns", "backlog/**", "--start", "main")
        packet = (self.repo / ".agent-runs/R1/prompts/R.md").read_text()
        self.assertIn(f"Kind: reconcile\nStart-SHA: {self.base}\n", packet)
        self.assertEqual(self.manifest()["assignments"]["R"]["start_sha"], self.base)
        self.assign("R2", "--kind", "reconcile", "--owns", "backlog/**",
                    "--start", "main", ok=False)
        self.assign("A3", "--owns", "src/**", ok=False)

    def test_review_is_bound_to_the_latest_result_head(self):
        self.start()
        self.review("ready", ok=False)
        self.submit()
        self.review("ready", head="0" * 40, ok=False)
        self.review("approved", ok=False)
        self.review("needs-fix")
        reviews = self.manifest()["assignments"]["A1"]["reviews"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["result"], "results/A1-1.json")
        self.assertEqual(reviews[0]["head_sha"], self.base)
        self.assertEqual(reviews[0]["verdict"], "needs-fix")
        self.assertEqual(reviews[0]["reviewer"], "operator")
        self.assertRegex(reviews[0]["utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_supervised_merge_needs_a_ready_review_of_the_latest_result(self):
        self.start()
        self.submit()
        self.merge(ok=False)
        self.review("needs-fix")
        self.merge(ok=False)
        self.review("ready")
        self.submit()
        self.merge(ok=False)
        self.review("ready")
        self.merge()
        self.assertEqual(self.manifest()["assignments"]["A1"]["state"], "merged")

    def test_supervised_close_records_behavior_delta(self):
        self.start()
        self.cli("resolve", "R1", "A1", "--outcome", "cancelled", "--evidence", "Stopped")
        self.close(ok=False)
        self.close("--delta", "sometimes", ok=False)
        self.close("--delta", "none")
        self.assertEqual(self.manifest()["behavior_delta"], "none")
        self.assertEqual(self.manifest()["state"], "closed")

    def test_version_one_close_refuses_behavior_delta(self):
        self.cli("init", "R1", "--base", "main")
        self.assign("A1")
        self.cli("resolve", "R1", "A1", "--outcome", "cancelled", "--evidence", "Stopped")
        self.close("--delta", "none", ok=False)
        self.close()

    def test_ledger_writes_wait_for_the_round_lock(self):
        self.start()
        with open(self.repo / ".agent-runs/R1/round.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            writer = subprocess.Popen(
                [
                    sys.executable, str(SCRIPT), "--repo", str(self.repo), "resolve",
                    "R1", "A1", "--outcome", "cancelled", "--evidence", "Stopped",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(0.5)
            self.assertIsNone(writer.poll())
            self.assertEqual(self.manifest()["assignments"]["A1"]["state"], "assigned")
        writer.communicate(timeout=10)
        self.assertEqual(writer.returncode, 0)
        self.assertEqual(self.manifest()["assignments"]["A1"]["state"], "cancelled")


if __name__ == "__main__":
    unittest.main()
