"""Deterministic Reconcile-loop supervisor (read-only preview). See SUPERVISION.md.

Each tick observes the ledger, Git, PRs/checks and session processes, then decides one next action.
This version performs no effects: `next` prints the decision, `status` explains it and
`run --dry-run` logs decisions while waiting. Exit codes: 0 action/wait/routine park,
10 needs attention, 11 transient or unknown observation, 2 configuration, 3 another instance runs.
"""

import argparse
import fcntl
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from supervisor import config, observe  # noqa: E402
from supervisor.decide import decide  # noqa: E402

STATE = ".agent-runs/supervisor"
PASSIVE = {"Wait"}


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_branch(repo, remote):
    done = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"],
        text=True, capture_output=True, check=False,
    )
    prefix = f"{remote}/"
    name = done.stdout.strip()
    return name[len(prefix):] if done.returncode == 0 and name.startswith(prefix) else "main"


def tick(repo, args, settings, autonomy, rounds_this_run=0):
    value = observe.snapshot(
        repo, settings, autonomy, args.branch,
        new_round=args.new_round, rounds_this_run=rounds_this_run,
    )
    return value, decide(value)


def describe(value, chosen):
    lines = [f"Autonomy: L{value['autonomy']}  default: {value['default_branch']}"
             f" @ {(value['remote']['default_sha'] or 'unknown')[:12]}"]
    manifest = value["round"]
    if manifest is None:
        closed = ", ".join(f"{r['id']}({r['delta']})" for r in value["rounds"]["closed"]) or "none"
        lines.append(f"Open round: none  closed: {closed}")
    else:
        lines.append(f"Open round: {manifest['id']} v{manifest['version']} base {manifest['base_sha'][:12]}")
        for aid, a in sorted(manifest["assignments"].items()):
            reviews = a.get("reviews") or []
            verdict = f" review={reviews[-1]['verdict']}" if reviews else ""
            lines.append(f"  {aid} {a['state']} {a['branch']} results={len(a['results'])}{verdict}")
        for name, s in sorted(manifest.get("sessions", {}).items()):
            lines.append(f"  {name} {s['role']} {s['state']} {s['assignment'] or '-'}")
        for h in manifest.get("halts", []):
            state = "cleared" if h["cleared_utc"] else "UNCLEARED"
            lines.append(f"  {h['id']} {state} {h['code']}: {h['detail']}")
    details = {k: v for k, v in chosen.items() if k not in {"kind", "exit"}}
    lines.append(f"Next: {chosen['kind']} (exit {chosen['exit']}) {json.dumps(details, sort_keys=True)}")
    return "\n".join(lines)


def hold_lock(repo):
    state = repo / STATE
    state.mkdir(parents=True, exist_ok=True)
    handle = (state / "lock").open("a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return None
    return handle


def record(repo, value, chosen, dry_run):
    entry = {"utc": utc_now(), "dry_run": dry_run, "round": (value["round"] or {}).get("id"),
             "action": chosen}
    state = repo / STATE
    with (state / "log.jsonl").open("a") as log:
        log.write(json.dumps(entry, sort_keys=True) + "\n")
    temporary = state / "last.json.tmp"
    temporary.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")
    temporary.replace(state / "last.json")


def run(repo, args, settings, autonomy):
    if not args.dry_run:
        print("Effects are not available in this version; use run --dry-run", file=sys.stderr)
        return 2
    ignored = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "-q", f"{STATE}/lock"], check=False
    )
    if ignored.returncode:
        print("Add .agent-runs/ to .gitignore before running the supervisor", file=sys.stderr)
        return 2
    lock = hold_lock(repo)
    if lock is None:
        print("Another supervisor instance holds the lock", file=sys.stderr)
        return 3
    while True:
        value, chosen = tick(repo, args, settings, autonomy)
        record(repo, value, chosen, dry_run=True)
        print(json.dumps(chosen, sort_keys=True), flush=True)
        if args.once or chosen["kind"] not in PASSIVE:
            # A dry run cannot perform the chosen effect, so the state will not advance further.
            return chosen["exit"]
        time.sleep(settings["supervisor"]["poll_seconds"])


def parser():
    command = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    command.add_argument("--repo", type=Path, default=Path.cwd())
    command.add_argument("--remote", default="origin")
    command.add_argument("--branch", help="Default branch (default: the remote's HEAD)")
    command.add_argument("--autonomy", type=int, choices=[1, 2, 3], help="Lower the level")
    actions = command.add_subparsers(dest="action", required=True)
    for name in ("next", "status", "run"):
        sub = actions.add_parser(name)
        sub.add_argument("--new-round", action="store_true", help="Allow one new round below L3")
        if name == "run":
            sub.add_argument("--once", action="store_true")
            sub.add_argument("--dry-run", action="store_true")
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    repo = args.repo.resolve()
    args.branch = args.branch or default_branch(repo, args.remote)
    try:
        settings = config.load(repo, args.remote, args.branch)
        if settings["supervisor"]["remote"] != args.remote:
            raise config.ConfigError(
                f"supervisor.remote is {settings['supervisor']['remote']!r}; pass --remote to match"
            )
        autonomy = config.effective_autonomy(settings, args.autonomy)
    except config.ConfigError as error:
        print(f"Configuration: {error}", file=sys.stderr)
        return 2
    try:
        if args.action == "run":
            return run(repo, args, settings, autonomy)
        value, chosen = tick(repo, args, settings, autonomy)
    except observe.ObservationError as error:
        print(f"Cannot observe: {error}", file=sys.stderr)
        return 10
    if args.action == "next":
        print(json.dumps(chosen, sort_keys=True))
    else:
        print(describe(value, chosen))
    return chosen["exit"]


if __name__ == "__main__":
    sys.exit(main())
