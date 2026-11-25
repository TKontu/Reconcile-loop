"""Optional merge guard: merge one reviewed PR only at its reviewed head, never operator-owned paths."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("merge_guard", ROOT / "scripts" / "merge_guard.py")
mg = importlib.util.module_from_spec(_spec)
sys.modules["merge_guard"] = mg
_spec.loader.exec_module(mg)

HEAD = "a" * 40
POLICY = mg.Policy(branch="main", method="squash", operator_paths=("docs/decisions/*", ".claude/*"))


class FakeGh:
    """Answers `gh pr view` and `gh pr diff --name-only`; records every call."""

    def __init__(self, files=("src/app.py",), **pr):
        self.pr = {
            "state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE",
            "headRefOid": HEAD, "baseRefName": "main", **pr,
        }  # fmt: skip
        self.files = list(files)
        self.calls = []
        self.merged = False
        self.merge_rc = 0

    def __call__(self, cmd):
        cmd = list(cmd)
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "pr", "view"]:
            return 0, json.dumps(dict(self.pr, state="MERGED" if self.merged else self.pr["state"]))
        if cmd[:3] == ["gh", "pr", "diff"]:
            return 0, "\n".join(self.files)
        if cmd[:3] == ["gh", "pr", "merge"]:
            self.merged = self.merge_rc == 0
            return self.merge_rc, "" if self.merge_rc == 0 else "boom"
        return 1, "unexpected"

    def merges(self):
        return [c for c in self.calls if c[:3] == ["gh", "pr", "merge"]]


class GuardTests(unittest.TestCase):
    def guard(self, gh, head=HEAD, policy=POLICY):
        return mg.guard(7, head, run=gh, policy=policy)

    def test_merges_the_reviewed_head_with_the_configured_method_and_confirms_it(self):
        gh = FakeGh()
        self.assertEqual(self.guard(gh), 0)
        [merge] = gh.merges()
        self.assertEqual(merge[merge.index("--match-head-commit") + 1], HEAD)
        self.assertIn("--squash", merge)
        self.assertEqual(gh.calls[-1][:3], ["gh", "pr", "view"])  # merge state re-read

    def test_refuses_unsafe_prs_without_merging(self):
        cases = [
            {"headRefOid": "b" * 40}, {"mergeable": "CONFLICTING"}, {"mergeable": "UNKNOWN"},
            {"isDraft": True}, {"state": "CLOSED"}, {"baseRefName": "feature"},
        ]  # fmt: skip
        for pr in cases:
            with self.subTest(pr):
                gh = FakeGh(**pr)
                self.assertEqual(self.guard(gh), 1)
                self.assertEqual(gh.merges(), [])

    def test_leaves_operator_owned_paths_to_the_operator(self):
        for path in ("docs/decisions/0003.md", ".claude/settings.json"):
            with self.subTest(path):
                gh = FakeGh(files=["src/app.py", path])
                self.assertEqual(self.guard(gh), 1)
                self.assertEqual(gh.merges(), [])

    def test_reads_every_changed_file_not_a_capped_list(self):
        files = [f"src/m{i}.py" for i in range(150)] + [".claude/settings.json"]
        gh = FakeGh(files=files)
        self.assertEqual(self.guard(gh), 1)
        self.assertTrue(any(c[:3] == ["gh", "pr", "diff"] and "--name-only" in c for c in gh.calls))

    def test_requires_a_full_head_sha(self):
        gh = FakeGh()
        self.assertEqual(self.guard(gh, head="abc123"), 2)
        self.assertEqual(gh.calls, [])

    def test_a_failed_merge_is_reported_as_not_merged(self):
        gh = FakeGh()
        gh.merge_rc = 1
        self.assertEqual(self.guard(gh), 1)


class PolicyTests(unittest.TestCase):
    def config(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        if text is not None:
            (root / ".agent").mkdir()
            (root / ".agent" / "config.toml").write_text(text)
        return root

    def test_defaults_protect_the_declared_governance_records_and_the_guard(self):
        root = self.config(
            '[project]\narchitecture = "docs/arch.md"\ndecisions = "docs/decisions"\n'
            'default_branch = "trunk"\n'
        )
        policy = mg.load_policy(root)
        self.assertEqual((policy.branch, policy.method), ("trunk", "merge"))
        for path in ("docs/arch.md", "docs/decisions/0001.md", "docs/decisions",
                     ".agent/config.toml", ".claude/settings.json", "scripts/merge_guard.py"):  # fmt: skip
            self.assertTrue(mg.owned(path, policy.operator_paths), path)
        self.assertFalse(mg.owned("src/app.py", policy.operator_paths))

    def test_configured_paths_and_method_are_used(self):
        root = self.config(
            '[merge_guard]\nmethod = "squash"\noperator_paths = ["SECURITY.md"]\n'
        )
        policy = mg.load_policy(root)
        self.assertEqual(policy.method, "squash")
        self.assertTrue(mg.owned("SECURITY.md", policy.operator_paths))
        self.assertTrue(mg.owned("scripts/merge_guard.py", policy.operator_paths))  # always

    def test_an_unreadable_config_or_bad_method_fails_closed(self):
        for text in ("[project\n", '[merge_guard]\nmethod = "force"\n',
                     '[merge_guard]\noperator_paths = "x"\n'):  # fmt: skip
            with self.subTest(text):
                with self.assertRaises(mg.GuardError):
                    mg.load_policy(self.config(text))

    def test_no_config_uses_the_built_in_defaults(self):
        policy = mg.load_policy(self.config(None))
        self.assertEqual(policy.branch, "main")
        self.assertTrue(mg.owned(".agent/config.toml", policy.operator_paths))


if __name__ == "__main__":
    unittest.main()
