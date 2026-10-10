"""Install or update the Reconcile-loop pack in a project, preserving local edits."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
LOCK = ".agent/pack.lock"
CORE = [
    "SPEC.md",
    ".agent/commands/*.md",
    ".agent/config.example.toml",
    "scripts/round.py",
    "templates/*",
    "examples/one-round.md",
]
RUNNERS = {
    "claude": [".claude/commands/*.md", ".claude/agents/*.md"],
    "codex": [".agents/skills/reconcile-loop/SKILL.md"],
}
RENAMED = {".agent/LICENSE": "LICENSE"}
IGNORED = [".agent-runs/", "HANDOFF.md"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo, *args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], text=True, stderr=subprocess.PIPE
        ).strip()
    except subprocess.CalledProcessError as error:
        raise ValueError(error.stderr.strip() or f"git {args[0]} failed") from None


def version():
    try:
        return git(PACK, "describe", "--tags", "--always", "--dirty")
    except (OSError, ValueError):
        return "unknown"


def sources(runners):
    """Map installed relative path to pack source for the selected runners."""
    files = {target: PACK / source for target, source in RENAMED.items()}
    for pattern in CORE + [p for runner in runners for p in RUNNERS[runner]]:
        for path in sorted(PACK.glob(pattern)):
            if path.is_file():
                files[path.relative_to(PACK).as_posix()] = path
    return files


def plan(repo, files, locked):
    """Return (action, path) pairs; local edits and foreign files are never replaced."""
    actions = []
    for name, source in files.items():
        target = repo / name
        new = digest(source)
        if not target.exists():
            actions.append(("skip-deleted" if name in locked else "add", name))
        elif digest(target) == new:
            actions.append(("same", name))
        elif locked.get(name) == digest(target):
            actions.append(("update", name))
        else:
            actions.append(("conflict", name))
    for name in sorted(set(locked) - set(files)):
        target = repo / name
        if target.exists() and digest(target) == locked[name]:
            actions.append(("remove", name))
        elif target.exists():
            actions.append(("keep-removed", name))
    return actions


def apply(repo, files, locked, actions):
    recorded = {}
    for action, name in actions:
        target = repo / name
        if action in {"add", "update"}:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(files[name].read_bytes())
        if action in {"add", "update", "same"}:
            recorded[name] = digest(target)
        elif action == "conflict":
            target.with_name(target.name + ".pack-new").write_bytes(files[name].read_bytes())
            if name in locked:
                recorded[name] = locked[name]
        elif action == "skip-deleted":
            recorded[name] = locked[name]
        elif action == "remove":
            target.unlink()
    return recorded


def ignore(repo):
    path = repo / ".gitignore"
    lines = path.read_text().splitlines() if path.exists() else []
    missing = [entry for entry in IGNORED if entry not in lines]
    if missing:
        path.write_text("".join(f"{line}\n" for line in lines + missing))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="project repository root")
    parser.add_argument("--claude", action="store_true", help="also install Claude Code files")
    parser.add_argument("--codex", action="store_true", help="also install the .agents skill")
    parser.add_argument("--dry-run", action="store_true", help="report actions only")
    args = parser.parse_args()
    try:
        repo = args.target.resolve()
        if repo == PACK:
            raise ValueError("Target is the pack itself")
        if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
            raise ValueError("Target must be a repository root")
        if not args.dry_run and git(repo, "status", "--porcelain"):
            raise ValueError("Start from a clean checkout")
        lock_path = repo / LOCK
        previous = json.loads(lock_path.read_text()) if lock_path.exists() else {}
        locked = previous.get("files", {})
        runners = sorted(
            set(previous.get("runners", []))
            | {name for name in RUNNERS if getattr(args, name)}
        )
        files = sources(runners)
        actions = plan(repo, files, locked)
        for action, name in actions:
            if action != "same":
                print(f"{action}: {name}")
        if args.dry_run:
            return 0
        recorded = apply(repo, files, locked, actions)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(
            json.dumps(
                {"version": 1, "pack": version(), "runners": runners, "files": recorded},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        ignore(repo)
        conflicts = [name for action, name in actions if action == "conflict"]
        if conflicts:
            print(f"Merge {len(conflicts)} *.pack-new file(s), then delete them.")
        print("Next: follow .agent/commands/bootstrap.md to configure the project.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Cannot install: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
