"""Small local round ledger. Run writes serially from one coordinator checkout."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

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
    save(
        root / "round.json",
        {
            "version": 1,
            "id": args.round,
            "base_sha": base,
            "state": "open",
            "assignments": {},
        },
    )


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
    packet.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"# Assignment {manifest['id']}/{args.assignment}\n\n"
        f"Base-SHA: {manifest['base_sha']}\nItem: {args.item}\nBranch: {args.branch}\n\n"
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
    }


def record(root, manifest, args):
    data = read(Path(args.result))
    assignment = manifest["assignments"][data["assignment"]]
    require(
        assignment["state"] not in {"merged", "cancelled"}, "Assignment is terminal"
    )
    bound_packet(root, assignment)
    validate_result(data, manifest, assignment)
    path = f"results/{data['assignment']}-{len(assignment['results']) + 1}.json"
    target = inside(root, path)
    require(
        not target.exists(), "Result already exists; inspect interrupted submission"
    )
    save(target, data)
    assignment["results"].append(path)
    assignment["state"] = "result-ready"


def resolve(repo, root, manifest, args):
    assignment = manifest["assignments"][args.assignment]
    require(
        assignment["state"] not in {"merged", "cancelled"}, "Assignment is terminal"
    )
    require(text(args.evidence), "Resolution needs review or cancellation evidence")
    if args.outcome == "merged":
        bound_packet(root, assignment)
        require(assignment["state"] == "result-ready", "No candidate result to resolve")
        result = read(inside(root, assignment["results"][-1]))
        validate_result(result, manifest, assignment)
        require(
            args.head == result["head_sha"],
            "Review does not match the current result head",
        )
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
    relative = inside(repo, args.reconciliation).relative_to(repo).as_posix()
    evidence = git(repo, "show", f"{final}:{relative}")
    require(evidence.strip(), "Reconciliation must be committed at final main")
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
    manifest.update(
        state="closed",
        final_main_sha=final,
        reconciliation=relative,
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
            for field in ("main", "reconciliation", "handoff", "evidence"):
                sub.add_argument(f"--{field}", required=True)
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
            manifest = read(root / "round.json")
            require(
                manifest["version"] == 1 and manifest["id"] == args.round,
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


if __name__ == "__main__":
    sys.exit(main())
