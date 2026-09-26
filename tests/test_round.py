"""Behavior checks for the local, single-coordinator round ledger."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "round.py"


class RoundTests(unittest.TestCase):
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
        self.spec.write_text("Document the approved behavior. Check whitespace.\n")

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
            self.assertNotEqual(result.returncode, 0)
        return result

    def start(self):
        self.cli("init", "R1", "--base", "main")
        self.cli(
            "assign",
            "R1",
            "A1",
            "--item",
            "TASK-1",
            "--branch",
            "docs/task",
            "--spec",
            str(self.spec),
        )

    def manifest(self):
        return json.loads((self.repo / ".agent-runs/R1/round.json").read_text())

    def submit(self, **changes):
        assignment = self.manifest()["assignments"]["A1"]
        data = {
            "assignment": "A1",
            "base_sha": self.base,
            "packet_sha256": assignment["packet_sha256"],
            "head_sha": self.base,
            "pr": "https://example.invalid/pull/1",
            "checks": [
                {
                    "command": ["git", "diff", "--check"],
                    "status": "passed",
                    "evidence": "PR check at the submitted head",
                }
            ],
        }
        data.update(changes)
        path = self.repo / ".agent-runs/result.json"
        path.write_text(json.dumps(data))
        return path

    def blocked_result(self, reason="Required fixture is missing"):
        path = self.submit(status="blocked", reason=reason)
        data = json.loads(path.read_text())
        for key in ("head_sha", "pr", "checks"):
            del data[key]
        path.write_text(json.dumps(data))
        return path

    def test_blocked_result_needs_no_pr_and_keeps_round_open(self):
        self.start()
        self.cli("record", "R1", "--result", str(self.blocked_result()))
        status = json.loads(self.cli("status", "R1").stdout)
        assignment = status["assignments"]["A1"]
        self.assertEqual(assignment["state"], "blocked")
        saved = json.loads(
            (self.repo / ".agent-runs/R1" / assignment["results"][-1]).read_text()
        )
        self.assertEqual(saved["reason"], "Required fixture is missing")
        self.assertNotIn("pr", saved)
        self.cli("init", "R2", "--base", "main", ok=False)
        self.cli(
            "close",
            "R1",
            "--main",
            "main",
            "--reconciliation",
            "README.md",
            "--handoff",
            "HANDOFF.md",
            "--evidence",
            "checks",
            ok=False,
        )

    def test_blocked_result_requires_reason(self):
        self.start()
        for reason in (None, "", " "):
            path = self.blocked_result(reason)
            if reason is None:
                data = json.loads(path.read_text())
                del data["reason"]
                path.write_text(json.dumps(data))
            rejected = self.cli("record", "R1", "--result", str(path), ok=False)
            self.assertIn("reason", rejected.stderr)
        self.assertEqual(self.manifest()["assignments"]["A1"]["results"], [])

    def test_blocked_result_invalidates_older_candidate_and_can_resume(self):
        self.start()
        self.cli("record", "R1", "--result", str(self.submit()))
        self.cli("record", "R1", "--result", str(self.blocked_result()))
        self.cli(
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
            "Old candidate review",
            ok=False,
        )
        self.cli("record", "R1", "--result", str(self.submit(status="result-ready")))
        assignment = self.manifest()["assignments"]["A1"]
        self.assertEqual(assignment["state"], "result-ready")
        self.assertEqual(len(assignment["results"]), 3)
        blocked = json.loads(
            (self.repo / ".agent-runs/R1" / assignment["results"][1]).read_text()
        )
        self.assertEqual(blocked["status"], "blocked")

    def test_blocked_assignment_can_cancel_but_not_reopen(self):
        self.start()
        path = self.blocked_result()
        self.cli("record", "R1", "--result", str(path))
        self.cli(
            "resolve",
            "R1",
            "A1",
            "--outcome",
            "cancelled",
            "--evidence",
            "Worker stopped",
        )
        self.cli("record", "R1", "--result", str(path), ok=False)
        self.assertEqual(self.manifest()["assignments"]["A1"]["state"], "cancelled")

    def test_unknown_result_status_is_rejected(self):
        self.start()
        self.cli(
            "record", "R1", "--result", str(self.submit(status="ready-ish")), ok=False
        )
        self.assertEqual(self.manifest()["assignments"]["A1"]["results"], [])

    def test_init_pins_base_and_status_is_read_only(self):
        self.cli("init", "R1", "--base", "main")
        self.assertEqual(self.manifest()["base_sha"], self.base)
        before = self.manifest()
        self.cli("status", "R1")
        self.assertEqual(self.manifest(), before)

    def test_second_round_requires_reconciliation(self):
        self.cli("init", "R1", "--base", "main")
        self.cli("init", "R2", "--base", "main", ok=False)
        self.assertFalse((self.repo / ".agent-runs/R2").exists())

    def test_assignment_is_bound_and_cannot_be_overwritten(self):
        self.start()
        a = self.manifest()["assignments"]["A1"]
        packet = self.repo / ".agent-runs/R1" / a["packet"]
        self.assertEqual(
            a["packet_sha256"], hashlib.sha256(packet.read_bytes()).hexdigest()
        )
        self.cli(
            "assign",
            "R1",
            "A1",
            "--item",
            "TASK-2",
            "--branch",
            "docs/other",
            "--spec",
            str(self.spec),
            ok=False,
        )
        self.assertIn("Document the approved behavior.", packet.read_text())

    def test_duplicate_item_or_branch_is_rejected(self):
        self.start()
        for item, branch in [("TASK-1", "docs/new"), ("TASK-2", "docs/task")]:
            self.cli(
                "assign",
                "R1",
                "A2",
                "--item",
                item,
                "--branch",
                branch,
                "--spec",
                str(self.spec),
                ok=False,
            )

    def test_cancelled_item_can_be_reassigned_without_reusing_branch(self):
        self.start()
        self.cli(
            "resolve",
            "R1",
            "A1",
            "--outcome",
            "cancelled",
            "--evidence",
            "Scope revised; worker stopped",
        )
        self.cli(
            "assign",
            "R1",
            "A2",
            "--item",
            "TASK-1",
            "--branch",
            "docs/revised",
            "--spec",
            str(self.spec),
        )
        self.assertEqual(self.manifest()["assignments"]["A1"]["state"], "cancelled")
        self.assertEqual(self.manifest()["assignments"]["A2"]["state"], "assigned")

    def test_packet_tampering_is_rejected(self):
        self.start()
        result = self.submit()
        packet = (
            self.repo
            / ".agent-runs/R1"
            / self.manifest()["assignments"]["A1"]["packet"]
        )
        packet.write_text("changed scope")
        self.cli("record", "R1", "--result", str(result), ok=False)

    def test_wrong_result_identity_is_rejected(self):
        self.start()
        for changes in [
            {"assignment": "A2"},
            {"base_sha": "f" * 40},
            {"packet_sha256": "f" * 64},
            {"head_sha": "abc"},
            {"checks": []},
        ]:
            result = self.submit(**changes)
            self.cli("record", "R1", "--result", str(result), ok=False)
        self.assertEqual(self.manifest()["assignments"]["A1"]["state"], "assigned")

    def test_results_are_retained_and_new_head_needs_new_review(self):
        self.start()
        self.cli("record", "R1", "--result", str(self.submit()))
        changed = self.submit(head_sha="3" * 40)
        self.cli("record", "R1", "--result", str(changed))
        self.assertEqual(
            len(list((self.repo / ".agent-runs/R1/results").glob("*.json"))), 2
        )
        self.cli(
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
            "reviewed old head",
            ok=False,
        )

    def test_failed_or_skipped_checks_do_not_resolve_as_merged(self):
        self.start()
        for status in ["failed", "skipped", "unavailable"]:
            result = self.submit(
                checks=[{"command": ["test"], "status": status, "evidence": "log"}]
            )
            self.cli("record", "R1", "--result", str(result))
            self.cli(
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
                "review",
                ok=False,
            )

    def test_close_rejects_unresolved_work(self):
        self.start()
        self.cli(
            "close",
            "R1",
            "--main",
            "main",
            "--reconciliation",
            "README.md",
            "--handoff",
            "HANDOFF.md",
            "--evidence",
            "checks",
            ok=False,
        )

    def test_cancel_reconcile_then_next_round(self):
        self.start()
        self.cli(
            "resolve",
            "R1",
            "A1",
            "--outcome",
            "cancelled",
            "--evidence",
            "Worker stopped; task returned to ready in the registry.",
        )
        self.cli("init", "R2", "--base", "main", ok=False)
        (self.repo / "reconcile.md").write_text(
            "TASK-1 returned to ready. No behavior changed.\n"
        )
        self.git("add", "reconcile.md")
        self.git("commit", "-qm", "reconcile cancelled assignment")
        final_sha = self.git("rev-parse", "HEAD")
        (self.repo / "HANDOFF.md").write_text(
            f"# Handoff\nMain-SHA: {final_sha}\nNext: plan TASK-1.\n"
        )
        self.cli(
            "close",
            "R1",
            "--main",
            "main",
            "--reconciliation",
            "reconcile.md",
            "--handoff",
            "HANDOFF.md",
            "--evidence",
            "final checks passed; no workers active",
        )
        self.assertEqual(self.manifest()["state"], "closed")
        self.cli("init", "R2", "--base", "main")

    def test_close_requires_committed_reconciliation_and_current_handoff(self):
        self.start()
        self.cli(
            "resolve", "R1", "A1", "--outcome", "cancelled", "--evidence", "Stopped"
        )
        (self.repo / "reconcile.md").write_text("Uncommitted evidence\n")
        (self.repo / "HANDOFF.md").write_text(f"Main-SHA: {self.base}\n")
        args = (
            "close",
            "R1",
            "--main",
            "main",
            "--reconciliation",
            "reconcile.md",
            "--handoff",
            "HANDOFF.md",
            "--evidence",
            "checks",
        )
        self.cli(*args, ok=False)
        self.git("add", "reconcile.md")
        self.git("commit", "-qm", "reconcile")
        self.cli(*args, ok=False)

    def test_merged_round_closes_and_terminal_result_cannot_change(self):
        self.start()
        result = self.submit()
        self.cli("record", "R1", "--result", str(result))
        self.cli(
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
            "Independent review and actual merge verified",
        )
        self.cli("record", "R1", "--result", str(result), ok=False)
        (self.repo / "HANDOFF.md").write_text(f"Main-SHA: {self.base}\n")
        self.cli(
            "close",
            "R1",
            "--main",
            "main",
            "--reconciliation",
            "README.md",
            "--handoff",
            "HANDOFF.md",
            "--evidence",
            "final check passed",
        )
        self.cli(
            "resolve",
            "R1",
            "A1",
            "--outcome",
            "cancelled",
            "--evidence",
            "late edit",
            ok=False,
        )

    def test_runtime_records_must_be_ignored(self):
        (self.repo / ".gitignore").write_text("HANDOFF.md\n")
        self.spec.unlink()
        self.git("add", ".gitignore")
        self.git("commit", "-qm", "remove runtime ignore")
        self.cli("init", "R1", "--base", "main", ok=False)
        self.assertFalse((self.repo / ".agent-runs/R1").exists())

    def test_unsafe_round_id_and_dirty_base_are_rejected(self):
        self.cli("init", "../outside", "--base", "main", ok=False)
        (self.repo / "README.md").write_text("dirty\n")
        self.cli("init", "R1", "--base", "main", ok=False)


if __name__ == "__main__":
    unittest.main()
