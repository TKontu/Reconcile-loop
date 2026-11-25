#!/usr/bin/env python3
"""Merge one reviewed PR only at its reviewed head, leaving operator-owned paths to the operator.

Optional helper: the core workflow never depends on it. Needs an authenticated `gh`.

    python3 scripts/merge_guard.py PR --head FULL_REVIEWED_SHA [--dry-run]

Use it when a planner merges under delegated authority (`[policy] merge_authority`), and make it
the only merge path by denying raw `gh pr merge` in your agent's permission settings. It merges
only when the PR is open, not a draft, mergeable, targets the default branch, still has exactly the
reviewed head and changes no operator-owned path. GitHub re-checks the head at merge time
(`--match-head-commit`), and the merge is confirmed by re-reading the PR. Review, the local gate
and whether a PR decides an operator-owned question are the planner's duties; this script cannot
see them.

Operator-owned paths: `.agent/config.toml`, `.claude/*` and this script always; then either
`[merge_guard] operator_paths` (glob patterns; a plain directory covers everything under it) or,
when that is unset, the `[project] architecture` and `decisions` records the config declares.
`[merge_guard] method` is `merge` (default), `squash` or `rebase`. A config that cannot be read
or a malformed `[merge_guard]` refuses every merge.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALWAYS = (".agent/config.toml", ".claude/*", "scripts/merge_guard.py")
METHODS = ("merge", "squash", "rebase")
Run = Callable[[Sequence[str]], tuple[int, str]]


class GuardError(RuntimeError):
    """The policy or the PR could not be read; nothing was merged."""


@dataclass(frozen=True)
class Policy:
    branch: str
    method: str
    operator_paths: tuple[str, ...]


def load_policy(root: Path = ROOT) -> Policy:
    path = root / ".agent" / "config.toml"
    try:
        config: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        config = {}
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise GuardError(f"cannot read {path}: {exc}") from exc
    project = config.get("project", {})
    guard = config.get("merge_guard", {})
    method = guard.get("method", "merge")
    if method not in METHODS:
        choices = ", ".join(METHODS)
        raise GuardError(f"[merge_guard] method must be one of {choices}, not {method!r}")
    configured = guard.get("operator_paths")
    if configured is None:
        extra = [str(project[k]) for k in ("architecture", "decisions") if project.get(k)]
    elif isinstance(configured, list) and all(isinstance(p, str) and p for p in configured):
        extra = list(configured)
    else:
        raise GuardError("[merge_guard] operator_paths must be a list of path patterns")
    return Policy(
        branch=str(project.get("default_branch", "main")),
        method=method,
        operator_paths=tuple(dict.fromkeys([*ALWAYS, *extra])),
    )


def owned(path: str, patterns: Iterable[str]) -> bool:
    """A glob match, or the path is a named directory or lies under one."""
    for pattern in patterns:
        bare = pattern.rstrip("/")
        if fnmatch.fnmatch(path, pattern) or path == bare or path.startswith(bare + "/"):
            return True
    return False


def _run(cmd: Sequence[str]) -> tuple[int, str]:
    try:
        done = subprocess.run(list(cmd), capture_output=True, text=True, timeout=120, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return done.returncode, (done.stdout + done.stderr).strip()


def view(pr: int, run: Run) -> dict[str, Any]:
    fields = "state,isDraft,mergeable,headRefOid,baseRefName"
    rc, out = run(["gh", "pr", "view", str(pr), "--json", fields])
    if rc:
        raise GuardError(f"gh pr view {pr} failed: {out[:300]}")
    try:
        record = json.loads(out)
    except json.JSONDecodeError as exc:
        raise GuardError(f"gh pr view {pr} returned no JSON: {out[:300]}") from exc
    if not isinstance(record, dict):
        raise GuardError(f"gh pr view {pr} returned {type(record).__name__}, not an object")
    return record


def changed_files(pr: int, run: Run) -> list[str]:
    """Every changed path (`gh pr view --json files` may cap the list)."""
    rc, out = run(["gh", "pr", "diff", str(pr), "--name-only"])
    if rc:
        raise GuardError(f"gh pr diff {pr} --name-only failed: {out[:300]}")
    return [line.strip() for line in out.splitlines() if line.strip()]


def problems(record: dict[str, Any], files: Sequence[str], head: str, policy: Policy) -> list[str]:
    found = []
    if record.get("state") != "OPEN":
        found.append(f"state is {record.get('state')}, not OPEN")
    if record.get("isDraft"):
        found.append("PR is a draft")
    if record.get("mergeable") != "MERGEABLE":
        found.append(f"mergeable is {record.get('mergeable')}")
    if record.get("baseRefName") != policy.branch:
        found.append(f"base is {record.get('baseRefName')}, not {policy.branch}")
    if record.get("headRefOid") != head:
        found.append(f"head is {record.get('headRefOid')}, not the reviewed {head}")
    if mine := sorted(f for f in files if owned(f, policy.operator_paths)):
        found.append("operator-owned paths, leave to the operator: " + ", ".join(mine))
    return found


def guard(
    pr: int, head: str, *, run: Run = _run, policy: Policy | None = None, dry_run: bool = False
) -> int:
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        print("refusing: --head must be the full 40-character reviewed SHA", file=sys.stderr)
        return 2
    try:
        policy = policy or load_policy()
        found = problems(view(pr, run), changed_files(pr, run), head, policy)
    except GuardError as exc:
        print(f"refusing PR #{pr}: {exc}", file=sys.stderr)
        return 1
    if found:
        for problem in found:
            print(f"refusing PR #{pr}: {problem}", file=sys.stderr)
        return 1
    if dry_run:
        print(f"PR #{pr} may be merged at {head} ({policy.method}); dry run, nothing merged")
        return 0
    rc, out = run(["gh", "pr", "merge", str(pr), f"--{policy.method}", "--match-head-commit", head])
    if rc:
        print(f"gh pr merge {pr} failed: {out[:300]}", file=sys.stderr)
        return 1
    try:
        state = view(pr, run).get("state")
    except GuardError as exc:
        print(f"PR #{pr}: merge sent but its state is unreadable ({exc}); check it", file=sys.stderr)
        return 1
    if state != "MERGED":
        print(f"PR #{pr} state is {state} after merge; not merged", file=sys.stderr)
        return 1
    print(f"merged PR #{pr} at reviewed head {head}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("pr", type=int)
    parser.add_argument("--head", required=True, help="full reviewed head SHA")
    parser.add_argument("--dry-run", action="store_true", help="check only; merge nothing")
    args = parser.parse_args(argv)
    return guard(args.pr, args.head, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
