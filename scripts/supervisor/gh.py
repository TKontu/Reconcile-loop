"""Thin, read-only GitHub CLI wrapper. Any failure is Unknown, never an empty success."""

import json
import subprocess

PR_FIELDS = "number,state,isDraft,headRefOid,headRefName,baseRefName,mergeable,mergeStateStatus,url"


class Unknown:
    def __init__(self, reason):
        self.reason = reason

    def __repr__(self):
        return f"Unknown({self.reason!r})"


def call(repo, *args):
    try:
        done = subprocess.run(
            ["gh", *args], cwd=repo, text=True, capture_output=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return Unknown(f"gh {args[0]}: {error}")
    if done.returncode:
        return Unknown(f"gh {args[0]} exited {done.returncode}: {done.stderr.strip()[:200]}")
    return done.stdout


def json_lines(text):
    try:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except json.JSONDecodeError as error:
        return Unknown(f"gh returned invalid JSON: {error}")


def pull_request(repo, branch):
    """The open PR for a branch, else the newest one; None when the branch has no PR."""
    out = call(repo, "pr", "list", "--head", branch, "--state", "all", "--json", PR_FIELDS)
    if isinstance(out, Unknown):
        return out
    try:
        prs = json.loads(out)
    except json.JSONDecodeError as error:
        return Unknown(f"gh pr list returned invalid JSON: {error}")
    if not prs:
        return None
    return sorted(prs, key=lambda p: (p["state"] == "OPEN", p["number"]))[-1]


def check_runs(repo, sha):
    out = call(
        repo, "api", "--paginate", f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs",
        "--jq", ".check_runs[] | {name, status, conclusion, id}",
    )
    return out if isinstance(out, Unknown) else json_lines(out)


def statuses(repo, sha):
    out = call(
        repo, "api", "--paginate", f"repos/{{owner}}/{{repo}}/commits/{sha}/statuses",
        "--jq", ".[] | {context, state, id}",
    )
    return out if isinstance(out, Unknown) else json_lines(out)
