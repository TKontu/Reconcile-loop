"""Small local round ledger. Run writes serially from one coordinator checkout."""

import argparse
import fcntl
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

FULL_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def commit(repo, ref):
    return git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")


def identifier(value):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value), "Unsafe identifier")
    return value


def inside(root, relative):
    require(
        text(relative) and not Path(relative).is_absolute(), "Expected a relative path"
    )
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), "Path escapes its record directory")
    return path


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def bound_packet(root, assignment):
    packet = inside(root, assignment["packet"])
    require(
        hashlib.sha256(packet.read_bytes()).hexdigest() == assignment["packet_sha256"],
        "Packet changed after assignment",
    )


def validate_result(data, manifest, assignment):
    require(data["base_sha"] == manifest["base_sha"], "Result base mismatch")
    require(
        data["packet_sha256"] == assignment["packet_sha256"], "Result packet mismatch"
    )
    status = data.get("status", "result-ready")
    require(status in {"result-ready", "blocked"}, "Unknown result status")
    if status == "blocked":
        require(text(data.get("reason")), "Blocked result needs a reason")
        return status
    require(
        isinstance(data["head_sha"], str) and FULL_SHA.fullmatch(data["head_sha"]),
        "Result needs a full head SHA",
    )
    require(text(data["pr"]), "Result needs a PR reference")
    require(
        isinstance(data["checks"], list) and data["checks"],
        "Result needs check evidence",
    )
    for check in data["checks"]:
        require(
            isinstance(check["command"], list)
            and check["command"]
            and all(text(arg) for arg in check["command"]),
            "Check needs command argv",
        )
        require(
            check["status"] in {"passed", "failed", "skipped", "unavailable"},
            "Unknown check status",
        )
        require(text(check["evidence"]), "Check needs an evidence reference or summary")
    return status


def initialize(repo, root, args):
    require(not root.exists(), "Round already exists")
    require(not git(repo, "status", "--porcelain"), "Start from a clean checkout")
    git(repo, "check-ignore", "-q", ".agent-runs/probe")
    base = commit(repo, args.base)
    for other in root.parent.glob("*/round.json"):
        require(
            read(other).get("state") == "closed",
            f"Unreconciled round: {other.parent.name}",
        )
    manifest = {
        "version": 1,
        "id": args.round,
        "base_sha": base,
        "state": "open",
        "assignments": {},
    }
    if args.supervised:
        manifest.update(version=2, sessions={}, halts=[])
    save(root / "round.json", manifest)


def assign(repo, root, manifest, args):
    identifier(args.assignment)
    assignments = manifest["assignments"]
    require(args.assignment not in assignments, "Assignment already exists")
    require(text(args.item), "Item must not be empty")
    git(repo, "check-ref-format", "--branch", args.branch)
    require(
        all(
            (a["item"] != args.item or a["state"] == "cancelled")
            and a["branch"] != args.branch
            for a in assignments.values()
        ),
        "Item or branch already assigned",
    )
    spec = Path(args.spec).read_text()
    require(spec.strip(), "Assignment spec is empty")
    relative = f"prompts/{args.assignment}.md"
    packet = inside(root, relative)
    require(
        not packet.exists(), "Packet already exists; inspect interrupted assignment"
    )
    supervision, fields = supervised_assignment(repo, manifest, args)
    packet.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"# Assignment {manifest['id']}/{args.assignment}\n\n"
        f"Base-SHA: {manifest['base_sha']}\nItem: {args.item}\nBranch: {args.branch}\n"
        + supervision
        + "\n"
        "Use an isolated checkout of this base. Return revision-bound evidence; do not merge.\n\n"
        + spec
    )
    packet.write_text(content)
    assignments[args.assignment] = {
        "item": args.item,
        "branch": args.branch,
        "packet": relative,
        "packet_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
        "state": "assigned",
        "results": [],
        **fields,
    }


def record(root, manifest, args):
    data = read(Path(args.result))
    assignment = manifest["assignments"][data["assignment"]]
    require(
        assignment["state"] not in {"merged", "cancelled"}, "Assignment is terminal"
    )
    bound_packet(root, assignment)
    status = validate_result(data, manifest, assignment)
    path = f"results/{data['assignment']}-{len(assignment['results']) + 1}.json"
    target = inside(root, path)
    require(
        not target.exists(), "Result already exists; inspect interrupted submission"
    )
    save(target, data)
    assignment["results"].append(path)
    assignment["state"] = status


def resolve(repo, root, manifest, args):
    assignment = manifest["assignments"][args.assignment]
    require(
        assignment["state"] not in {"merged", "cancelled"}, "Assignment is terminal"
    )
    require(text(args.evidence), "Resolution needs review or cancellation evidence")
    if supervised(manifest):
        merging = {"merger"} if args.outcome == "merged" else set()
        require_no_live_sessions(manifest, args.assignment, allow=merging)
    if args.outcome == "merged":
        bound_packet(root, assignment)
        require(assignment["state"] == "result-ready", "No candidate result to resolve")
        result = read(inside(root, assignment["results"][-1]))
        validate_result(result, manifest, assignment)
        require(
            args.head == result["head_sha"],
            "Review does not match the current result head",
        )
        if supervised(manifest):
            require_ready_review(assignment, args.head)
        require(
            all(c["status"] == "passed" for c in result["checks"]),
            "Not all checks passed",
        )
        require(
            args.merge and FULL_SHA.fullmatch(args.merge),
            "Supply the actual full merge SHA",
        )
        assignment["merge_sha"] = commit(repo, args.merge)
        assignment["reviewed_head"] = args.head
    assignment["state"] = args.outcome
    assignment["resolution"] = args.evidence


def close(repo, root, manifest, args):
    require(
        all(
            a["state"] in {"merged", "cancelled"}
            for a in manifest["assignments"].values()
        ),
        "Unresolved assignments remain",
    )
    final = commit(repo, args.main)
    for assignment in manifest["assignments"].values():
        if assignment["state"] == "merged":
            git(repo, "merge-base", "--is-ancestor", assignment["merge_sha"], final)
    reference = args.reconciliation
    url = urlsplit(reference)
    if url.scheme:
        require(
            url.scheme in {"https", "http"} and url.hostname,
            "Reconciliation URL needs HTTP(S) and a host",
        )
    else:
        reference = inside(repo, reference).relative_to(repo).as_posix()
        evidence = git(repo, "show", f"{final}:{reference}")
        require(
            evidence.strip(),
            "Local reconciliation evidence must be committed at final main",
        )
    handoff = inside(repo, args.handoff).read_text()
    require(
        f"Main-SHA: {final}" in handoff.splitlines(),
        "Handoff must name the final main SHA",
    )
    require(
        len(handoff.splitlines()) <= 50 and len(handoff.split()) <= 500,
        "Handoff is too long",
    )
    require(text(args.evidence), "Closure needs final verification evidence")
    supervised_close(manifest, args)
    manifest.update(
        state="closed",
        final_main_sha=final,
        reconciliation=reference,
        handoff=args.handoff,
        closure_evidence=args.evidence,
    )


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--repo", type=Path, default=Path.cwd())
    actions = command.add_subparsers(dest="action", required=True)
    for name in ("init", "assign", "record", "resolve", "close", "status"):
        sub = actions.add_parser(name)
        sub.add_argument("round")
        if name == "init":
            sub.add_argument("--base", required=True)
        elif name == "assign":
            sub.add_argument("assignment")
            for field in ("item", "branch", "spec"):
                sub.add_argument(f"--{field}", required=True)
        elif name == "record":
            sub.add_argument("--result", required=True)
        elif name == "resolve":
            sub.add_argument("assignment")
            sub.add_argument(
                "--outcome", choices=["merged", "cancelled"], required=True
            )
            sub.add_argument("--head")
            sub.add_argument("--merge")
            sub.add_argument("--evidence", required=True)
        elif name == "close":
            sub.add_argument(
                "--reconciliation",
                required=True,
                help="Tracked file path or HTTP(S) reconciliation evidence URL",
            )
            for field in ("main", "handoff", "evidence"):
                sub.add_argument(f"--{field}", required=True)
    add_supervised_arguments(actions)
    return command


def main():
    args = parser().parse_args()
    try:
        repo = args.repo.resolve()
        require(
            Path(git(repo, "rev-parse", "--show-toplevel")).resolve() == repo,
            "--repo must name the repository root",
        )
        root = inside(repo, f".agent-runs/{identifier(args.round)}")
        if args.action == "init":
            initialize(repo, root, args)
        else:
            hold_lock(root)
            manifest = read(root / "round.json")
            require(
                manifest["version"] in VERSIONS and manifest["id"] == args.round,
                "Unsupported or mismatched round record",
            )
            if args.action == "status":
                print(json.dumps(manifest, indent=2))
                return 0
            require(manifest["state"] == "open", "Round is closed")
            if args.action == "assign":
                assign(repo, root, manifest, args)
            elif args.action == "record":
                record(root, manifest, args)
            elif args.action == "resolve":
                resolve(repo, root, manifest, args)
            elif args.action == "close":
                close(repo, root, manifest, args)
            elif args.action == "review":
                review(root, manifest, args)
            elif args.action == "session":
                session(root, manifest, args)
            elif args.action == "halt":
                halt(manifest, args)
            elif args.action == "clear-halt":
                clear_halt(manifest, args)
            save(root / "round.json", manifest)
        print(f"{args.round}: {args.action} recorded")
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Cannot {args.action}: {error}", file=sys.stderr)
        return 1


# Supervised (version 2) rounds. These records let an unattended supervisor drive a round without
# interpreting prose; see SUPERVISION.md. Version 1 rounds behave exactly as on main.

VERSIONS = {1, 2}
LIVE = {"assigned", "blocked", "result-ready"}
TERMINAL = {"merged", "cancelled"}
_LOCK = []


def hold_lock(root):
    """Serialize ledger writers on this host until the process exits."""
    if root.is_dir():
        handle = (root / "round.lock").open("a")
        fcntl.flock(handle, fcntl.LOCK_EX)
        _LOCK.append(handle)


def supervised(manifest):
    return manifest["version"] == 2


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def static_prefix(pattern):
    return re.split(r"[*?\[]", pattern, maxsplit=1)[0]


def supervised_assignment(repo, manifest, args):
    """Validate ownership options; return extra packet lines and manifest fields."""
    if not supervised(manifest):
        require(
            not (args.owns or args.resource or args.kind or args.start),
            "Ownership options need a supervised round",
        )
        return "", {}
    kind = args.kind or "work"
    owns = args.owns or []
    resources = args.resource or []
    require(
        owns and all(text(p) and not p.startswith("/") for p in owns),
        "Supervised assignment needs relative --owns paths",
    )
    require(all(text(r) for r in resources), "Resource names must not be empty")
    others = manifest["assignments"].values()
    require(
        not any(
            a["kind"] == "reconcile" and a["state"] != "cancelled" for a in others
        ),
        "Round is already reconciling",
    )
    lines = f"Kind: {kind}\n"
    start = None
    if kind == "reconcile":
        require(
            all(a["state"] in TERMINAL for a in others),
            "Work assignments must be terminal before reconciliation",
        )
        require(text(args.start), "Reconcile assignment needs --start")
        start = commit(repo, args.start)
        lines += f"Start-SHA: {start}\n"
    else:
        require(args.start is None, "--start is only for reconcile assignments")
        mine = [static_prefix(p) for p in owns]
        for other in (a for a in others if a["state"] in LIVE):
            for theirs in map(static_prefix, other["owned_paths"]):
                require(
                    not any(p.startswith(theirs) or theirs.startswith(p) for p in mine),
                    "Owned paths overlap a live assignment",
                )
            require(
                not set(resources) & set(other["resources"]),
                "Resource is held by a live assignment",
            )
    lines += "".join(f"Owned-Path: {p}\n" for p in owns)
    lines += "".join(f"Resource: {r}\n" for r in resources)
    fields = {
        "kind": kind,
        "owned_paths": owns,
        "resources": resources,
        "start_sha": start,
        "reviews": [],
    }
    return lines, fields


def latest_review(assignment):
    reviews = [r for r in assignment["reviews"] if r["result"] == assignment["results"][-1]]
    return reviews[-1] if reviews else None


def require_ready_review(assignment, head):
    current = latest_review(assignment)
    require(
        current and current["verdict"] == "ready" and current["head_sha"] == head,
        "Supervised merge needs a ready review of the latest result head",
    )


def review(root, manifest, args):
    require(supervised(manifest), "Reviews need a supervised round")
    assignment = manifest["assignments"][args.assignment]
    require(assignment["state"] == "result-ready", "No candidate result to review")
    latest = assignment["results"][-1]
    result = read(inside(root, latest))
    require(args.head == result["head_sha"], "Review does not match the latest result head")
    require(text(args.evidence), "Review needs an evidence reference")
    if args.session:
        reviewer = manifest["sessions"].get(args.session)
        require(
            reviewer
            and reviewer["role"] == "reviewer"
            and reviewer["assignment"] == args.assignment
            and reviewer["head_sha"] == args.head
            and reviewer["state"] == "exited",
            "Review session must be a finished reviewer of this head",
        )
    else:
        require(text(args.reviewer), "Review needs a reviewer")
    assignment["reviews"].append(
        {
            "result": latest,
            "head_sha": args.head,
            "verdict": args.verdict,
            "evidence": args.evidence,
            "reviewer": args.reviewer,
            "session": args.session,
            "utc": utc_now(),
        }
    )


def supervised_close(manifest, args):
    if not supervised(manifest):
        require(args.delta is None, "--delta needs a supervised round")
        return
    require(args.delta is not None, "Supervised closure needs --delta changed|none")
    require_no_live_sessions(manifest)
    require_no_halts(manifest)
    manifest["behavior_delta"] = args.delta


LIVE_SESSION = {"launching", "running"}
UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\Z")


def require_supervised(manifest):
    require(supervised(manifest), "Sessions and halts need a supervised round")


def require_no_halts(manifest):
    require(
        all(h["cleared_utc"] for h in manifest["halts"]), "Round has an uncleared halt"
    )


def require_no_live_sessions(manifest, assignment=None, allow=frozenset()):
    for name, record in manifest["sessions"].items():
        require(
            record["state"] not in LIVE_SESSION
            or record["role"] in allow
            or (assignment is not None and record["assignment"] != assignment),
            f"Session {name} is still live",
        )


def utc_value(value):
    require(text(value) and UTC.match(value), "Expected YYYY-MM-DDTHH:MM:SSZ")
    datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return value


def session(root, manifest, args):
    require_supervised(manifest)
    sessions = manifest["sessions"]
    if args.step == "start":
        start_session(root, manifest, args)
        return
    record = sessions[args.session]
    if args.step == "ack":
        require(record["state"] == "launching", "Only a launching session can be acknowledged")
        require(args.pid > 0, "Process id must be positive")
        record.update(pid=args.pid, state="running")
        return
    require(record["state"] in LIVE_SESSION, "Session has already ended")
    require(args.cost_usd is None or args.cost_usd >= 0, "Cost must not be negative")
    if args.imported:
        require(inside(root, args.imported).is_file(), "Imported record does not exist")
    record.update(
        state=args.state,
        exit_code=args.exit_code,
        cost_usd=args.cost_usd,
        imported=args.imported,
        ended_utc=utc_now(),
    )


def start_session(root, manifest, args):
    require_no_halts(manifest)
    sessions = manifest["sessions"]
    for field in ("runner", "session_uuid", "cwd"):
        require(text(getattr(args, field)), f"Session needs --{field.replace('_', '-')}")
    require(
        all(s["session_uuid"] != args.session_uuid for s in sessions.values()),
        "Session UUID already recorded",
    )
    utc_value(args.deadline)
    if args.role == "planner":
        require(args.assignment is None, "Planner sessions take no assignment")
        require(
            not any(
                s["role"] == "planner" and s["state"] in LIVE_SESSION
                for s in sessions.values()
            ),
            "A planner session is already live",
        )
    else:
        assignment = manifest["assignments"][args.assignment]
        require(
            not any(
                s["assignment"] == args.assignment and s["state"] in LIVE_SESSION
                for s in sessions.values()
            ),
            "Assignment already has a live session",
        )
        current = latest_review(assignment) if assignment["results"] else None
        if args.role == "executor":
            require(
                assignment["state"] == "assigned"
                or (
                    assignment["state"] == "result-ready"
                    and current
                    and current["verdict"] == "needs-fix"
                ),
                "Executor needs an assigned or needs-fix assignment",
            )
        elif args.role == "reviewer":
            require(assignment["state"] == "result-ready", "No candidate result to review")
            result = read(inside(root, assignment["results"][-1]))
            require(args.head == result["head_sha"], "Reviewer head is not the latest result")
            require(current is None, "Latest result already has a review")
        else:
            require(assignment["state"] == "result-ready", "No candidate result to merge")
            require_ready_review(assignment, args.head)
    name = f"S{len(sessions) + 1}"
    sessions[name] = {
        "role": args.role,
        "assignment": args.assignment,
        "procedure": args.procedure,
        "runner": args.runner,
        "session_uuid": args.session_uuid,
        "cwd": args.cwd,
        "head_sha": args.head,
        "pid": None,
        "started_utc": utc_now(),
        "deadline_utc": args.deadline,
        "state": "launching",
        "exit_code": None,
        "cost_usd": None,
        "imported": None,
        "ended_utc": None,
    }
    print(json.dumps({"session": name}))


def halt(manifest, args):
    require_supervised(manifest)
    for field in ("code", "detail", "action"):
        require(text(getattr(args, field)), f"Halt needs --{field}")
    if args.assignment is not None:
        require(args.assignment in manifest["assignments"], "Unknown assignment")
    if args.session is not None:
        require(args.session in manifest["sessions"], "Unknown session")
    inventory = read(Path(args.inventory)) if args.inventory else None
    manifest["halts"].append(
        {
            "id": f"H{len(manifest['halts']) + 1}",
            "utc": utc_now(),
            "code": args.code,
            "assignment": args.assignment,
            "session": args.session,
            "detail": args.detail,
            "action": args.action_needed,
            "inventory": inventory,
            "cleared_utc": None,
            "cleared_evidence": None,
        }
    )


def clear_halt(manifest, args):
    require_supervised(manifest)
    matches = [h for h in manifest["halts"] if h["id"] == args.halt]
    require(matches, "Unknown halt")
    require(matches[0]["cleared_utc"] is None, "Halt already cleared")
    require(text(args.evidence), "Clearing a halt needs evidence")
    matches[0].update(cleared_utc=utc_now(), cleared_evidence=args.evidence)


def add_session_arguments(actions):
    sub = actions.add_parser("session")
    steps = sub.add_subparsers(dest="step", required=True)
    start = steps.add_parser("start")
    start.add_argument("round")
    start.add_argument(
        "--role", choices=["planner", "executor", "reviewer", "merger"], required=True
    )
    start.add_argument("--assignment")
    start.add_argument("--head")
    start.add_argument("--procedure")
    for field in ("runner", "session-uuid", "cwd", "deadline"):
        start.add_argument(f"--{field}", required=True)
    ack = steps.add_parser("ack")
    ack.add_argument("round")
    ack.add_argument("session")
    ack.add_argument("--pid", type=int, required=True)
    end = steps.add_parser("end")
    end.add_argument("round")
    end.add_argument("session")
    end.add_argument(
        "--state", choices=["exited", "timed-out", "killed", "lost"], required=True
    )
    end.add_argument("--exit-code", type=int)
    end.add_argument("--cost-usd", type=float)
    end.add_argument("--imported", help="Record path inside the round directory")
    sub = actions.add_parser("halt")
    sub.add_argument("round")
    for field in ("code", "detail"):
        sub.add_argument(f"--{field}", required=True)
    sub.add_argument("--action", dest="action_needed", required=True)
    sub.add_argument("--assignment")
    sub.add_argument("--session")
    sub.add_argument("--inventory", help="JSON file listing live sessions and resources")
    sub = actions.add_parser("clear-halt")
    sub.add_argument("round")
    sub.add_argument("halt")
    sub.add_argument("--evidence", required=True)


def add_supervised_arguments(actions):
    actions.choices["init"].add_argument("--supervised", action="store_true")
    assign_parser = actions.choices["assign"]
    assign_parser.add_argument("--owns", action="append", help="Owned path glob")
    assign_parser.add_argument("--resource", action="append")
    assign_parser.add_argument("--kind", choices=["work", "reconcile"])
    assign_parser.add_argument("--start", help="Reconcile start revision")
    actions.choices["close"].add_argument("--delta", choices=["changed", "none"])
    sub = actions.add_parser("review")
    sub.add_argument("round")
    sub.add_argument("assignment")
    sub.add_argument("--head", required=True)
    sub.add_argument(
        "--verdict", choices=["ready", "needs-fix", "blocked"], required=True
    )
    sub.add_argument("--evidence", required=True)
    who = sub.add_mutually_exclusive_group(required=True)
    who.add_argument("--reviewer")
    who.add_argument("--session", help="Finished reviewer session")
    add_session_arguments(actions)


if __name__ == "__main__":
    sys.exit(main())
