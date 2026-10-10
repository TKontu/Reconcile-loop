"""Supervisor configuration: validation, committed-policy source and autonomy grants."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from supervisor import config  # noqa: E402

EXAMPLE = (ROOT / ".agent/supervisor.example.toml").read_text()

L2 = """
[supervisor]
autonomy = 2
[policy.merge]
auto_merge = true
required_checks = ["check"]
"""

L3 = L2.replace("autonomy = 2", "autonomy = 3") + """
[policy.reconcile]
auto_reconcile = true
allow_reconcile_merge = true
"""


class ParseTests(unittest.TestCase):
    def test_example_is_valid_and_conservative(self):
        settings = config.parse(EXAMPLE)
        self.assertEqual(settings["supervisor"]["autonomy"], 1)
        self.assertFalse(settings["policy"]["merge"]["auto_merge"])
        self.assertEqual(config.effective_autonomy(settings), 1)
        self.assertIn("planner", settings["runner"]["roles"])

    def test_defaults_fill_an_empty_file(self):
        settings = config.parse("")
        self.assertEqual(settings["supervisor"]["max_parallel"], 1)
        self.assertEqual(settings["stop"]["max_repairs"], 2)

    def test_rejections_name_the_problem(self):
        cases = [
            ("[supervisor]\nautonmy = 1\n", "supervisor.autonmy"),
            ("[surpervisor]\n", "surpervisor"),
            ("[supervisor]\nautonomy = 4\n", "supervisor.autonomy"),
            ("[supervisor]\nmax_parallel = 0\n", "supervisor.max_parallel"),
            ("[supervisor]\nmax_parallel = true\n", "supervisor.max_parallel"),
            ("[budgets]\nround_usd = -1\n", "budgets.round_usd"),
            ("[policy.merge]\nauto_merge = 1\n", "policy.merge.auto_merge"),
            ("[policy.merge]\nmethod = 'fast'\n", "policy.merge.method"),
            ("[policy.merge]\nrequired_checks = 'check'\n", "policy.merge.required_checks"),
            ("[notify]\ncommand = [1]\n", "notify.command"),
            ("[runner.commands.x]\nargv = []\n", "runner.commands.x.argv"),
            ("[runner.roles.boss]\nmodel = 'x'\n", "runner.roles.boss"),
            ("[runner.roles.planner]\ntimeout_minutes = 0\n", "timeout_minutes"),
            ("not toml [", "TOML"),
        ]
        for text, fragment in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaises(config.ConfigError) as caught:
                    config.parse(text)
                self.assertIn(fragment, str(caught.exception))

    def test_local_override_is_limited_to_runner_and_budgets(self):
        settings = config.parse(EXAMPLE, "[budgets]\nround_usd = 3.5\n")
        self.assertEqual(settings["budgets"]["round_usd"], 3.5)
        settings = config.parse(EXAMPLE, "[runner.roles.executor]\nmodel = 'local'\n")
        self.assertEqual(settings["runner"]["roles"]["executor"]["model"], "local")
        self.assertEqual(settings["runner"]["roles"]["planner"]["model"], "opus")
        for local in ("[policy.merge]\nauto_merge = true\n", "[supervisor]\nautonomy = 3\n"):
            with self.subTest(local=local):
                with self.assertRaises(config.ConfigError) as caught:
                    config.parse(EXAMPLE, local)
                self.assertIn("local", str(caught.exception))


class AutonomyTests(unittest.TestCase):
    def test_grants_are_required(self):
        with self.assertRaises(config.ConfigError) as caught:
            config.effective_autonomy(config.parse("[supervisor]\nautonomy = 2\n"))
        self.assertIn("auto_merge", str(caught.exception))
        missing_checks = L2.replace('required_checks = ["check"]', "required_checks = []")
        with self.assertRaises(config.ConfigError) as caught:
            config.effective_autonomy(config.parse(missing_checks))
        self.assertIn("required_checks", str(caught.exception))
        with self.assertRaises(config.ConfigError) as caught:
            config.effective_autonomy(config.parse(L2.replace("autonomy = 2", "autonomy = 3")))
        self.assertIn("auto_reconcile", str(caught.exception))
        self.assertEqual(config.effective_autonomy(config.parse(L2)), 2)
        self.assertEqual(config.effective_autonomy(config.parse(L3)), 3)

    def test_ceiling_can_lower_but_never_raise(self):
        self.assertEqual(config.effective_autonomy(config.parse(L3), ceiling=1), 1)
        self.assertEqual(config.effective_autonomy(config.parse(EXAMPLE), ceiling=3), 1)


class LoadTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.origin = Path(tmp.name) / "origin.git"
        self.repo = Path(tmp.name) / "project"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        subprocess.run(["git", "clone", "-q", self.origin, self.repo], check=True,
                       capture_output=True)
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / ".gitignore").write_text(".agent-runs/\n.agent/supervisor.local.toml\n")
        self.settings = self.repo / ".agent/supervisor.toml"
        self.settings.parent.mkdir()
        self.settings.write_text("[supervisor]\nautonomy = 1\n")
        self.git("add", ".")
        self.git("commit", "-qm", "policy")
        self.git("push", "-q", "origin", "main")

    def git(self, *args):
        subprocess.run(["git", "-C", self.repo, *args], check=True, capture_output=True)

    def test_policy_comes_from_the_committed_remote_branch(self):
        self.settings.write_text(L3)
        settings = config.load(self.repo, "origin", "main")
        self.assertEqual(settings["supervisor"]["autonomy"], 1)
        self.assertEqual(
            Path(settings["supervisor"]["worktree_root"]),
            self.repo.parent / "project-worktrees",
        )

    def test_missing_committed_policy_fails(self):
        with self.assertRaises(config.ConfigError) as caught:
            config.load(self.repo, "origin", "develop")
        self.assertIn("origin/develop", str(caught.exception))

    def test_local_override_must_be_ignored(self):
        local = self.repo / ".agent/supervisor.local.toml"
        local.write_text("[budgets]\nround_usd = 1.0\n")
        self.assertEqual(config.load(self.repo, "origin", "main")["budgets"]["round_usd"], 1.0)
        (self.repo / ".gitignore").write_text(".agent-runs/\n")
        with self.assertRaises(config.ConfigError) as caught:
            config.load(self.repo, "origin", "main")
        self.assertIn("ignored", str(caught.exception))

    def test_worktree_root_must_be_outside_the_repository(self):
        self.settings.write_text("[supervisor]\nworktree_root = 'trees'\n")
        self.git("commit", "-qam", "inside")
        self.git("push", "-q", "origin", "main")
        with self.assertRaises(config.ConfigError) as caught:
            config.load(self.repo, "origin", "main")
        self.assertIn("worktree_root", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
