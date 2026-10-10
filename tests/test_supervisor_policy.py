"""Pure merge-policy checks for the supervisor: globs, required checks and the L2 gate."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from supervisor import policy  # noqa: E402

HEAD = "a" * 40


def run(name, conclusion="success", status="completed", id=1):
    return {"name": name, "status": status, "conclusion": conclusion, "id": id}


def facts(**changes):
    value = {
        "kind": "work",
        "branch": "task/a1",
        "default_branch": "main",
        "result_head": HEAD,
        "review": {"verdict": "ready", "head_sha": HEAD},
        "pr": {
            "state": "OPEN",
            "isDraft": False,
            "headRefOid": HEAD,
            "headRefName": "task/a1",
            "baseRefName": "main",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
        },
        "checks": "passed",
        "checks_timed_out": False,
        "files": ["docs/guide.md"],
        "changed_lines": 12,
        "owned_paths": ["docs/**"],
    }
    value.update(changes)
    return value


def pr(**changes):
    return {**facts()["pr"], **changes}


GATE = {
    "required_checks": ["check"],
    "protected_paths": [".github/**", ".agent/supervisor.toml"],
    "max_changed_lines": 400,
    "allow_reconcile_merge": False,
}


class GlobTests(unittest.TestCase):
    def test_glob_semantics(self):
        cases = [
            ("docs/a.md", "docs/**", True),
            ("docs/x/y/a.md", "docs/**", True),
            ("docs", "docs/**", False),
            ("docsx/a.md", "docs/**", False),
            ("src/a.py", "src/*.py", True),
            ("src/x/a.py", "src/*.py", False),
            ("src/x/a.py", "src/**/*.py", True),
            ("src/a.py", "src/**/*.py", True),
            ("README.md", "README.md", True),
            ("README.mdx", "README.md", False),
            ("a1.txt", "a?.txt", True),
            ("ab.txt", "a[0-9].txt", False),
            ("a.b", "a.b", True),
            ("axb", "a.b", False),
        ]
        for path, pattern, expected in cases:
            with self.subTest(path=path, pattern=pattern):
                self.assertEqual(policy.glob_match(path, pattern), expected)


class RequiredCheckTests(unittest.TestCase):
    def test_all_required_successes_pass(self):
        state, detail = policy.required_checks_state(
            ["check", "lint"], [run("check"), run("lint"), run("optional", "failure")], []
        )
        self.assertEqual(state, "passed")
        self.assertEqual(detail, {"check": "success", "lint": "success"})

    def test_newest_run_wins(self):
        runs = [run("check", "failure", id=1), run("check", "success", id=2)]
        self.assertEqual(policy.required_checks_state(["check"], runs, [])[0], "passed")
        runs = [run("check", "success", id=3), run("check", "failure", id=4)]
        self.assertEqual(policy.required_checks_state(["check"], runs, [])[0], "failed")

    def test_non_success_conclusions_fail(self):
        for conclusion in ("failure", "skipped", "neutral", "cancelled", "timed_out", None):
            with self.subTest(conclusion=conclusion):
                state, _ = policy.required_checks_state(["check"], [run("check", conclusion)], [])
                self.assertEqual(state, "failed")

    def test_missing_required_check_fails(self):
        state, detail = policy.required_checks_state(["check"], [run("other")], [])
        self.assertEqual(state, "failed")
        self.assertEqual(detail, {"check": "missing"})

    def test_incomplete_run_is_pending(self):
        state, _ = policy.required_checks_state(
            ["check"], [run("check", None, status="in_progress")], []
        )
        self.assertEqual(state, "pending")

    def test_commit_statuses_count(self):
        statuses = [{"context": "ci/legacy", "state": "pending", "id": 1}]
        self.assertEqual(policy.required_checks_state(["ci/legacy"], [], statuses)[0], "pending")
        statuses.append({"context": "ci/legacy", "state": "success", "id": 2})
        self.assertEqual(policy.required_checks_state(["ci/legacy"], [], statuses)[0], "passed")
        statuses.append({"context": "ci/legacy", "state": "error", "id": 3})
        self.assertEqual(policy.required_checks_state(["ci/legacy"], [], statuses)[0], "failed")

    def test_no_required_checks_never_passes(self):
        self.assertEqual(policy.required_checks_state([], [run("check")], [])[0], "failed")


class MergeGateTests(unittest.TestCase):
    def assertGate(self, value, verdict, reason=None):
        result, reasons = policy.merge_gate(value, GATE)
        self.assertEqual(result, verdict, reasons)
        if reason:
            self.assertIn(reason, reasons)

    def test_clean_reviewed_pr_merges(self):
        self.assertGate(facts(), "merge")
        self.assertGate(facts(pr=pr(mergeStateStatus="HAS_HOOKS")), "merge")

    def test_holds(self):
        cases = [
            (facts(review=None), "no-ready-review"),
            (facts(review={"verdict": "needs-fix", "head_sha": HEAD}), "no-ready-review"),
            (facts(review={"verdict": "ready", "head_sha": "b" * 40}), "no-ready-review"),
            (facts(pr=pr(state="CLOSED")), "pr-not-open"),
            (facts(pr=pr(state="MERGED")), "pr-not-open"),
            (facts(pr=pr(isDraft=True)), "pr-draft"),
            (facts(pr=pr(headRefOid="b" * 40)), "head-moved"),
            (facts(pr=pr(headRefName="other")), "wrong-head-branch"),
            (facts(pr=pr(baseRefName="develop")), "wrong-base"),
            (facts(pr=pr(mergeable="CONFLICTING", mergeStateStatus="DIRTY")), "conflicting"),
            (facts(pr=pr(mergeStateStatus="BEHIND")), "behind"),
            (facts(pr=pr(mergeStateStatus="UNSTABLE")), "merge-state-UNSTABLE"),
            (facts(pr=pr(mergeStateStatus="BLOCKED")), "merge-state-BLOCKED"),
            (facts(checks="failed"), "checks-failed"),
            (facts(checks="pending", checks_timed_out=True), "checks-timeout"),
            (facts(files=["docs/a.md", "src/x.py"]), "outside-owned:src/x.py"),
            (
                facts(files=[".github/workflows/x.yml"], owned_paths=["**"]),
                "protected:.github/workflows/x.yml",
            ),
            (facts(changed_lines=401), "too-large"),
            (facts(binary=["docs/logo.png"]), "binary:docs/logo.png"),
            (facts(files=None), "diff-unavailable"),
            (facts(files=[]), "empty-diff"),
            (facts(kind="reconcile"), "reconcile-merge-not-granted"),
        ]
        for value, reason in cases:
            with self.subTest(reason=reason):
                self.assertGate(value, "hold", reason)

    def test_waits(self):
        self.assertGate(facts(checks="pending"), "wait", "checks-pending")
        self.assertGate(facts(checks="pending", pr=pr(mergeStateStatus="BLOCKED")), "wait")
        self.assertGate(facts(pr=pr(mergeable="UNKNOWN", mergeStateStatus="UNKNOWN")), "wait")

    def test_hold_wins_over_wait(self):
        self.assertGate(facts(checks="pending", changed_lines=999), "hold", "too-large")

    def test_reconcile_merge_with_grant(self):
        gate = {**GATE, "allow_reconcile_merge": True}
        self.assertEqual(policy.merge_gate(facts(kind="reconcile"), gate)[0], "merge")


if __name__ == "__main__":
    unittest.main()
