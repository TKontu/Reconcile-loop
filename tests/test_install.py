"""Behavior checks for installing and updating the pack in an adopting repository."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = [
    "SPEC.md",
    ".agent/commands/takeoff.md",
    ".agent/config.example.toml",
    ".agent/LICENSE",
    "scripts/round.py",
    "templates/assignment.md",
    "examples/one-round.md",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.pack = base / "pack"
        shutil.copytree(
            ROOT,
            self.pack,
            ignore=shutil.ignore_patterns(".git", ".agent-runs", "__pycache__"),
        )
        self.repo = base / "project"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / "README.md").write_text("Project\n")
        (self.repo / ".gitignore").write_text("build/\n")
        self.commit("base")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], text=True
        ).strip()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def install(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(self.pack / "scripts/install.py"), str(self.repo), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def lock(self):
        return json.loads((self.repo / ".agent/pack.lock").read_text())

    def test_fresh_install_copies_core_and_records_hashes(self):
        self.install()
        for path in CORE:
            self.assertTrue((self.repo / path).is_file(), path)
        self.assertFalse((self.repo / ".claude").exists())
        self.assertFalse((self.repo / ".agents").exists())
        self.assertFalse((self.repo / ".agent/config.toml").exists())
        self.assertEqual((self.repo / "README.md").read_text(), "Project\n")
        lock = self.lock()
        self.assertEqual(lock["runners"], [])
        self.assertEqual(lock["files"]["SPEC.md"], digest(self.repo / "SPEC.md"))
        ignored = (self.repo / ".gitignore").read_text().splitlines()
        self.assertEqual(ignored[0], "build/")
        self.assertIn(".agent-runs/", ignored)
        self.assertIn("HANDOFF.md", ignored)
        help_text = subprocess.run(
            [sys.executable, str(self.repo / "scripts/round.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_text.returncode, 0, help_text.stderr)

    def test_runner_wrappers_are_opt_in_and_remembered(self):
        self.install("--claude", "--codex")
        self.assertTrue((self.repo / ".claude/commands/takeoff.md").is_file())
        self.assertTrue((self.repo / ".agents/skills/reconcile-loop/SKILL.md").is_file())
        self.assertEqual(self.lock()["runners"], ["claude", "codex"])
        self.commit("install")
        (self.pack / ".claude/commands/takeoff.md").write_text("new wrapper\n")
        self.install()
        self.assertEqual(
            (self.repo / ".claude/commands/takeoff.md").read_text(), "new wrapper\n"
        )

    def test_installed_links_resolve(self):
        self.install("--claude", "--codex")
        for file in self.repo.rglob("*.md"):
            if ".git" in file.relative_to(self.repo).parts:
                continue
            for target in re.findall(r"\]\(([^)]+)\)", file.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                if file.name == "README.md" and file.parent == self.repo:
                    continue
                self.assertTrue(
                    (file.parent / target.split("#")[0]).is_file(),
                    f"{file.relative_to(self.repo)}: {target}",
                )

    def test_update_replaces_unmodified_and_preserves_local_edits(self):
        self.install()
        (self.repo / "SPEC.md").write_text("local protocol edit\n")
        self.commit("install and adapt")
        (self.pack / "SPEC.md").write_text("upstream protocol\n")
        (self.pack / "templates/item.md").write_text("upstream item\n")
        result = self.install()
        self.assertEqual((self.repo / "SPEC.md").read_text(), "local protocol edit\n")
        self.assertEqual(
            (self.repo / "SPEC.md.pack-new").read_text(), "upstream protocol\n"
        )
        self.assertEqual((self.repo / "templates/item.md").read_text(), "upstream item\n")
        self.assertIn("SPEC.md", result.stdout)
        self.assertEqual(
            self.lock()["files"]["templates/item.md"],
            digest(self.repo / "templates/item.md"),
        )

    def test_existing_project_file_is_not_overwritten(self):
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts/round.py").write_text("project script\n")
        self.commit("own script")
        self.install()
        self.assertEqual((self.repo / "scripts/round.py").read_text(), "project script\n")
        self.assertTrue((self.repo / "scripts/round.py.pack-new").is_file())
        self.assertNotIn("scripts/round.py", self.lock()["files"])

    def test_removed_pack_file_is_deleted_only_when_unmodified(self):
        self.install()
        (self.repo / "templates/handoff.md").write_text("kept locally\n")
        self.commit("install")
        (self.pack / "templates/item.md").unlink()
        (self.pack / "templates/handoff.md").unlink()
        self.install()
        self.assertFalse((self.repo / "templates/item.md").exists())
        self.assertEqual((self.repo / "templates/handoff.md").read_text(), "kept locally\n")
        self.assertNotIn("templates/item.md", self.lock()["files"])

    def test_locally_deleted_file_stays_deleted_across_updates(self):
        self.install()
        (self.repo / "examples/one-round.md").unlink()
        self.commit("drop example")
        self.install()
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.install()
        self.assertFalse((self.repo / "examples/one-round.md").exists())

    def test_dirty_checkout_dry_run_and_self_target_are_refused_or_inert(self):
        (self.repo / "README.md").write_text("dirty\n")
        rejected = self.install(ok=False)
        self.assertIn("clean", rejected.stderr)
        self.assertFalse((self.repo / ".agent").exists())
        self.install("--dry-run")
        self.git("checkout", "--", "README.md")
        planned = self.install("--dry-run")
        self.assertIn("SPEC.md", planned.stdout)
        self.assertFalse((self.repo / ".agent").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")
        own = subprocess.run(
            [sys.executable, str(self.pack / "scripts/install.py"), str(self.pack)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(own.returncode, 0)


if __name__ == "__main__":
    unittest.main()
