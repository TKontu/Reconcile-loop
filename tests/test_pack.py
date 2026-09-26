"""Check that the copyable instructions remain connected after packaging edits."""

import json
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackTests(unittest.TestCase):
    def test_all_local_markdown_links_resolve(self):
        for file in ROOT.rglob("*.md"):
            if any(
                part in {".git", ".agent-runs"} for part in file.relative_to(ROOT).parts
            ):
                continue
            for target in re.findall(r"\]\(([^)]+)\)", file.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                self.assertTrue(
                    (file.parent / target.split("#")[0]).is_file(),
                    f"{file.relative_to(ROOT)}: {target}",
                )

    def test_config_and_result_templates_are_parseable(self):
        config = tomllib.loads((ROOT / ".agent/config.example.toml").read_text())
        self.assertIsInstance(config["verification"]["command"], list)
        result = json.loads((ROOT / "templates/result.json").read_text())
        self.assertEqual(result["checks"][0]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
