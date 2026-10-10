"""Pure merge-policy helpers. No I/O: callers pass observations in and act on the verdict."""

import re

PASSING_RUN = {"success"}
PENDING_RUN = {"queued", "in_progress", "waiting", "pending", "requested"}
STATUS_OUTCOME = {"success": "success", "pending": "pending", "failure": "failed", "error": "failed"}
MERGE_STATES = {"CLEAN", "HAS_HOOKS"}


def glob_regex(pattern):
    """Translate a path glob: `**` spans directories, `*` and `?` stay within one segment."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        elif pattern[i] == "[" and "]" in pattern[i + 2 :]:
            end = pattern.index("]", i + 2)
            body = pattern[i + 1 : end].replace("\\", "\\\\")
            out.append(f"[{'^' if body.startswith('!') else ''}{body.lstrip('!')}]")
            i = end + 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def glob_match(path, pattern):
    if pattern.endswith("/**") and path == pattern[:-3]:
        return False
    return bool(glob_regex(pattern).match(path))


def required_checks_state(required, runs, statuses):
    """Return (passed|pending|failed, {name: outcome}) for the required names at one SHA.

    Check runs take precedence over legacy commit statuses of the same name; within a source the
    newest (highest id) wins. Missing, skipped, neutral and cancelled count as failed.
    """
    detail = {}
    for name in required:
        mine = sorted((r for r in runs if r["name"] == name), key=lambda r: r["id"])
        if mine:
            newest = mine[-1]
            if newest["status"] != "completed":
                detail[name] = "pending" if newest["status"] in PENDING_RUN else "failed"
            else:
                detail[name] = "success" if newest["conclusion"] in PASSING_RUN else "failed"
            continue
        legacy = sorted((s for s in statuses if s["context"] == name), key=lambda s: s["id"])
        detail[name] = STATUS_OUTCOME.get(legacy[-1]["state"], "failed") if legacy else "missing"
    if not required or any(v in {"failed", "missing"} for v in detail.values()):
        return "failed", detail
    if any(v == "pending" for v in detail.values()):
        return "pending", detail
    return "passed", detail


def merge_gate(facts, gate):
    """Return (merge|wait|hold, reasons). Any hold reason wins over waiting."""
    holds, waits = [], []
    head = facts["result_head"]
    review = facts["review"]
    if not (review and review["verdict"] == "ready" and review["head_sha"] == head):
        holds.append("no-ready-review")
    pr = facts["pr"]
    if pr["state"] != "OPEN":
        holds.append("pr-not-open")
    if pr["isDraft"]:
        holds.append("pr-draft")
    if pr["headRefOid"] != head:
        holds.append("head-moved")
    if pr["headRefName"] != facts["branch"]:
        holds.append("wrong-head-branch")
    if pr["baseRefName"] != facts["default_branch"]:
        holds.append("wrong-base")
    checks = facts["checks"]
    if checks == "failed":
        holds.append("checks-failed")
    elif checks == "pending" and facts["checks_timed_out"]:
        holds.append("checks-timeout")
    elif checks == "pending":
        waits.append("checks-pending")
    state = pr["mergeStateStatus"]
    if pr["mergeable"] == "CONFLICTING" or state == "DIRTY":
        holds.append("conflicting")
    elif state == "BEHIND":
        holds.append("behind")
    elif pr["mergeable"] == "UNKNOWN" or state == "UNKNOWN":
        waits.append("mergeability-unknown")
    elif state not in MERGE_STATES and not (state == "BLOCKED" and checks == "pending"):
        holds.append(f"merge-state-{state}")
    files = facts["files"]
    if files is None:
        holds.append("diff-unavailable")
    elif not files:
        holds.append("empty-diff")
    else:
        for path in files:
            if not any(glob_match(path, p) for p in facts["owned_paths"]):
                holds.append(f"outside-owned:{path}")
            if any(glob_match(path, p) for p in gate["protected_paths"]):
                holds.append(f"protected:{path}")
        if facts["changed_lines"] > gate["max_changed_lines"]:
            holds.append("too-large")
        # Binary changes have no line count, so they cannot be checked against the size limit.
        holds += [f"binary:{path}" for path in facts.get("binary", [])]
    if facts["kind"] == "reconcile" and not gate["allow_reconcile_merge"]:
        holds.append("reconcile-merge-not-granted")
    if holds:
        return "hold", holds
    if waits:
        return "wait", waits
    return "merge", []
