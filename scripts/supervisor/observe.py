"""Collect one read-only observation snapshot for decide(): ledger, Git, PRs/checks and processes."""

import json
import subprocess
import sys
import time
from pathlib import Path

from . import gh, policy
from .decide import LIVE_SESSION, latest_review

ROUND_PY = Path(__file__).resolve().parents[1] / "round.py"
RUNS = ".agent-runs"
SESSIONS = f"{RUNS}/supervisor/sessions"


class ObservationError(ValueError):
    """Local state that cannot be read safely; the supervisor stops instead of guessing."""


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
    )


def remote_head(repo, remote, branch):
    done = git(repo, "ls-remote", "--exit-code", remote, f"refs/heads/{branch}")
    if done.returncode or not done.stdout.strip():
        return None, f"git ls-remote {remote} {branch} failed: {done.stderr.strip()[:200]}"
    return done.stdout.split()[0], None


def checkout(repo, remote_sha):
    clean = not git(repo, "status", "--porcelain").stdout.strip()
    on_default = None
    if remote_sha and not git(repo, "cat-file", "-e", f"{remote_sha}^{{commit}}").returncode:
        on_default = not git(repo, "merge-base", "--is-ancestor", "HEAD", remote_sha).returncode
    return {"clean": clean, "head_on_default": on_default}


def round_order(name):
    return (0, int(name[1:]), name) if name[:1] == "R" and name[1:].isdigit() else (1, 0, name)


def rounds(repo):
    open_ids, closed, ids = [], [], []
    for path in sorted((repo / RUNS).glob("*/round.json"), key=lambda p: round_order(p.parent.name)):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise ObservationError(f"Unreadable round record {path}: {error}") from None
        ids.append(path.parent.name)
        if data.get("state") == "closed":
            closed.append({"id": path.parent.name, "delta": data.get("behavior_delta")})
        else:
            open_ids.append(path.parent.name)
    return {"open": open_ids, "closed": closed, "ids": ids}


def ledger(repo, round_id):
    """Read the open round through round.py so the read takes the ledger lock."""
    done = subprocess.run(
        [sys.executable, str(ROUND_PY), "--repo", str(repo), "status", round_id],
        text=True, capture_output=True, check=False,
    )
    if done.returncode:
        raise ObservationError(f"round.py status {round_id}: {done.stderr.strip()}")
    return json.loads(done.stdout)


def latest_results(repo, manifest):
    found = {}
    for aid, a in manifest["assignments"].items():
        if a["results"]:
            path = repo / RUNS / manifest["id"] / a["results"][-1]
            try:
                found[aid] = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as error:
                raise ObservationError(f"Unreadable result {path}: {error}") from None
    return found


def process(repo, record):
    """A session process is alive only if its pid runs a command naming the session UUID."""
    uuid = record["session_uuid"]
    exit_file = repo / SESSIONS / f"{uuid}.exit.json"
    pid_file = repo / SESSIONS / f"{uuid}.pid"
    pid = record.get("pid")
    if pid is None and pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            pid = None
    exit_record = None
    if exit_file.exists():
        try:
            exit_record = json.loads(exit_file.read_text())
        except json.JSONDecodeError:
            exit_record = {"code": None, "invalid": True}
    alive = False
    if pid:
        shown = subprocess.run(
            ["ps", "-o", "args=", "-p", str(pid)], text=True, capture_output=True, check=False
        )
        alive = shown.returncode == 0 and uuid in shown.stdout
    return {"pid": pid, "alive": alive, "exit": exit_record}


def diff(repo, start, head):
    names = git(repo, "diff", "--name-only", "--no-renames", start, head)
    counts = git(repo, "diff", "--numstat", "--no-renames", start, head)
    if names.returncode or counts.returncode:
        return {"files": None, "changed_lines": 0, "binary": []}
    total, binary = 0, []
    for line in counts.stdout.splitlines():
        added, removed, path = line.split("\t", 2)
        if added == "-":
            binary.append(path)
        else:
            total += int(added) + int(removed)
    return {"files": names.stdout.splitlines(), "changed_lines": total, "binary": binary}


def required_checks(repo, gate, head):
    runs = gh.check_runs(repo, head)
    states = gh.statuses(repo, head)
    for value in (runs, states):
        if isinstance(value, gh.Unknown):
            return {"unknown": value.reason}
    state, detail = policy.required_checks_state(gate["required_checks"], runs, states)
    return {"state": state, "detail": detail}


def worktree(path):
    if not path.exists():
        return {"exists": False, "dirty": False}
    done = git(path, "status", "--porcelain")
    return {"exists": True, "dirty": bool(done.returncode or done.stdout.strip())}


def snapshot(repo, settings, autonomy, branch, new_round=False, rounds_this_run=0, now=None):
    repo = Path(repo).resolve()
    supervisor = settings["supervisor"]
    merge_policy = settings["policy"]["merge"]
    default_sha, unknown = remote_head(repo, supervisor["remote"], branch)
    value = {
        "now": now if now is not None else time.time(),
        "autonomy": autonomy,
        "new_round": new_round,
        "rounds_this_run": rounds_this_run,
        "default_branch": branch,
        "limits": {
            "max_parallel": supervisor["max_parallel"],
            "launch_grace_seconds": supervisor["launch_grace_seconds"],
            "sessions_per_round": settings["budgets"]["sessions_per_round"],
            "round_usd": settings["budgets"]["round_usd"],
            "max_rounds_per_run": settings["budgets"]["max_rounds_per_run"],
            "ci_timeout_minutes": settings["budgets"]["ci_timeout_minutes"],
            "max_repairs": settings["stop"]["max_repairs"],
            "stall_rounds": settings["stop"]["stall_rounds"],
        },
        "gate": {
            "required_checks": merge_policy["required_checks"],
            "protected_paths": merge_policy["protected_paths"],
            "max_changed_lines": merge_policy["max_changed_lines"],
            "allow_reconcile_merge": settings["policy"]["reconcile"]["allow_reconcile_merge"],
        },
        "remote": {"default_sha": default_sha, "unknown": unknown},
        "checkout": checkout(repo, default_sha),
        "rounds": rounds(repo),
        "round": None,
        "results": {},
        "processes": {},
        "prs": {},
        "checks": {},
        "diffs": {},
        "worktrees": {},
        "final_gate": None,
    }
    if len(value["rounds"]["open"]) != 1:
        return value
    manifest = ledger(repo, value["rounds"]["open"][0])
    value["round"] = manifest
    if manifest["version"] != 2:
        return value
    value["results"] = latest_results(repo, manifest)
    for name, record in manifest["sessions"].items():
        if record["state"] in LIVE_SESSION and record["role"] != "merger":
            value["processes"][name] = process(repo, record)
    trees = Path(supervisor["worktree_root"]) / manifest["id"]
    for aid, a in manifest["assignments"].items():
        if a["state"] in {"merged", "cancelled"}:
            value["worktrees"][aid] = worktree(trees / aid)
        if a["state"] != "result-ready":
            continue
        pr = gh.pull_request(repo, a["branch"])
        value["prs"][aid] = {"unknown": pr.reason} if isinstance(pr, gh.Unknown) else {"pr": pr}
        review = latest_review(a)
        head = value["results"][aid]["head_sha"]
        if autonomy >= 2 and review and review["verdict"] == "ready" and review["head_sha"] == head:
            value["checks"][aid] = required_checks(repo, value["gate"], head)
            value["diffs"][aid] = diff(repo, a["start_sha"] or manifest["base_sha"], head)
    gate_file = repo / RUNS / "supervisor" / manifest["id"] / "final-gate.json"
    if gate_file.exists():
        value["final_gate"] = json.loads(gate_file.read_text()).get("state")
    return value

