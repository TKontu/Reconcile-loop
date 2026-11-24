#!/usr/bin/env python3
"""Live lanes for the optional round supervisor: start, probe and release them by rule.

Optional add-on: the core workflow never depends on it. Needs POSIX, Herdr (or ``setsid`` for a
command lane outside Herdr), git and an authenticated ``gh``. See .agent/supervisor.md.

A lane whose work outlasts the round must not be a child of the orchestrator's session: its
subagents and background commands end with it. ``start`` opens Herdr tab ``live-<repo>-<lane>``
in the supervisor's own workspace (cwd = the lane worktree) and either starts a named Herdr agent
there (``--agent KIND``) or runs a generated wrapper around a launcher script (``--cmd SCRIPT``).
The wrapper writes ``runner.pid``, appends output to ``runner.log`` and, when the launcher returns,
writes its exit code and time to ``runner.rc``. Outside Herdr a command lane runs under
``setsid -f nohup``. The record lives in ``.agent-runs/lanes/<lane>/lane.json``.

``status`` probes each record: ``running``, ``done`` (rc 0; write-up owed), ``recorded`` (written
up, set by ``recorded``), ``blocked`` (non-zero rc, or the agent waits on approval), ``dead`` (no
process and no rc; prints the resume command) or ``unknown`` (Herdr cannot be asked). An idle agent
is still ``running``: only its result and PR say it finished.

``cleanup`` releases finished lanes; a dry run unless ``--go``. Lane worktrees are registered
worktrees at a sibling path (``<repo>-...``) or a record's cwd. One is removed with plain
``git worktree remove`` once the newest PR on its branch is merged or closed and none is open.
A lane tab is closed with ``herdr tab close`` only when every pane in it is settled, its worktree
is gone or removed in this run and its lane is not carried. Anything uncertain is held and
reported, never forced: ``carried`` (HANDOFF.md names it), ``no-pr``, ``open-pr``, ``dirty``,
``unpushed``, ``busy`` (a process has its cwd inside; ``busy-unknown`` without /proc),
``lane <x> <state>`` (its record is not done or recorded), ``active`` and ``foreign`` (a pane
outside the lane paths). Planner, loop, supervisor, manager and review-server tabs are never closed.

    start LANE --cwd DIR (--cmd SCRIPT | --agent KIND) [--branch B] | status [--json]
    recorded LANE [--note TEXT] | cleanup [--go]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("ROUND_SUPERVISOR_ROOT", Path(__file__).resolve().parents[1]))
SELF = Path(__file__).resolve()
LANE_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,47}")
PROTECTED = re.compile(r"round[-_ ]?loop|review[-_ ]?server|planner|supervisor|manager", re.I)
SETTLED = {"idle", "done", "unknown", None}  # any other pane state keeps the tab
RELEASABLE = {"done", "recorded"}  # a record in any other state keeps its tab and worktree
DELETED = " (deleted)"
Run = Callable[..., tuple[int, str]]


class LaneError(RuntimeError):
    """A precondition failed; nothing was started or changed."""


def _run(cmd: Sequence[str], timeout: float = 120) -> tuple[int, str]:
    try:
        done = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return done.returncode, done.stdout.strip() or done.stderr.strip()


def _pid_alive(pid: int, wrapper: str) -> bool:
    """Alive and running ``wrapper``, so a recycled pid reads as gone (``kill 0`` without /proc)."""
    if Path("/proc/self/cmdline").exists():
        try:
            argv = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        except OSError:
            return False
        return os.fsencode(wrapper) in argv
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _spawn(argv: list[str], cwd: Path, log: Path) -> None:
    """``setsid -f`` forks the detached child and returns at once."""
    with log.open("ab") as sink:
        try:
            subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=sink, stderr=sink, check=True)
        except FileNotFoundError as exc:
            raise LaneError(f"{exc.filename} not found; cannot detach the lane") from exc
        except (OSError, subprocess.CalledProcessError) as exc:
            raise LaneError(f"detaching failed ({exc}); see {log}") from exc


def _cwds() -> list[str] | None:
    """Every other live process's cwd, or None when the process table cannot be read."""
    if not Path("/proc/self/cwd").exists():
        return None
    cwds = []
    for proc in Path("/proc").glob("[0-9]*"):
        if proc.name == str(os.getpid()):
            continue
        try:
            cwds.append(os.readlink(proc / "cwd"))
        except OSError:
            continue
    return cwds


@dataclass
class Seams:
    run: Run
    in_herdr: Callable[[], bool]
    pid_alive: Callable[[int, str], bool]
    spawn: Callable[[list[str], Path, Path], None]
    cwds: Callable[[], list[str] | None]


def default_seams() -> Seams:
    return Seams(
        run=_run,
        in_herdr=lambda: bool(os.environ.get("HERDR_ENV")) and shutil.which("herdr") is not None,
        pid_alive=_pid_alive,
        spawn=_spawn,
        cwds=_cwds,
    )


def _herdr(seams: Seams, *args: str) -> dict[str, Any] | None:
    """A subcommand's ``result``; ``{"_error": code}`` when Herdr reports one; None if unreachable."""
    rc, out = seams.run(["herdr", *args], 60)
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        return None if rc else {}
    if not isinstance(payload, dict):
        return None
    if rc:
        error = payload.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        return {"_error": str(code)} if code else None
    result = payload.get("result")
    return result if isinstance(result, dict) else {}


def _ok(result: dict[str, Any] | None) -> bool:
    return result is not None and "_error" not in result


def lane_prefix(root: Path = ROOT) -> str:
    """The supervisor's naming rule: ``live-<slug>-``, slug from ``[supervisor] name`` or the dir."""
    try:
        raw = tomllib.loads((root / ".agent" / "config.toml").read_text()).get("supervisor", {})
        raw = raw.get("name")
    except (OSError, tomllib.TOMLDecodeError):
        raw = None
    slug = re.sub(r"[^a-z0-9]+", "-", str(raw or root.name).lower()).strip("-") or "repo"
    return f"live-{slug}-"


def lanes_dir(root: Path) -> Path:
    return root / ".agent-runs" / "lanes"  # .agent-runs/ is already gitignored by bootstrap


def load_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(lanes_dir(root).glob("*/lane.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and record.get("lane"):
            records.append(record)
    return records


def _record_path(root: Path, lane: str) -> Path:
    return lanes_dir(root) / lane / "lane.json"


def _save(root: Path, record: dict[str, Any]) -> None:
    path = _record_path(root, record["lane"])
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _wrapper(script: Path, cwd: Path, out: Path, header: str) -> Path:
    pid, log, rc = (shlex.quote(str(out / n)) for n in ("runner.pid", "runner.log", "runner.rc"))
    body = f"""#!/usr/bin/env bash
# {header}
# Generated by scripts/lanes.py start; re-run that, never this file by hand.
# runner.pid: line 1 is this wrapper's pid (what `status` probes), line 2 the launcher's.
set -u
set -m  # the launcher gets its own process group, so a forwarded signal reaches all of it
cd {shlex.quote(str(cwd))} || exit 2
rm -f {rc}
child= pending=
# A signal can land after the fork but before child=$! runs: keep it, never drop it.
forward() {{ if [ -n "$child" ]; then kill -s "$1" "-$child" 2>/dev/null || kill -s "$1" "$child" 2>/dev/null; else pending=$1; fi; }}
trap 'forward TERM' TERM
trap 'forward INT' INT
trap 'forward HUP' HUP
bash {shlex.quote(str(script))} >> {log} 2>&1 &
child=$!; [ -z "$pending" ] || forward "$pending"
printf '%s\\nchild %s\\n' "$$" "$child" > {pid}
# Never `wait` while a trap can interrupt it: an interrupted wait can lose the launcher's status.
while kill -0 "$child" 2>/dev/null; do sleep 0.2; done
trap '' TERM INT HUP  # the launcher is gone: nothing left to forward
wait "$child"; status=$?
printf '%s\\n%s\\n' "$status" "$(date -u +%FT%TZ)" > {rc}
exit "$status"
"""
    path = out / "live_runner.sh"
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def start(
    lane: str,
    *,
    cwd: Path,
    cmd: Path | None,
    agent: str | None,
    branch: str = "",
    root: Path = ROOT,
    prefix: str | None = None,
    seams: Seams | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Launch the lane outside the caller's session and return its saved record."""
    seams = seams or default_seams()
    env = os.environ if env is None else env
    if not LANE_RE.fullmatch(lane):
        raise LaneError(f"lane name {lane!r}: use lowercase letters, digits and '-'")
    if (agent is None) == (cmd is None):
        raise LaneError("give exactly one of --agent KIND or --cmd SCRIPT")
    label = (prefix or lane_prefix(root)) + lane
    out = lanes_dir(root) / lane
    if (previous := _record_path(root, lane)).is_file():
        state, detail = probe(json.loads(previous.read_text(encoding="utf-8")), seams)
        if state in ("running", "blocked", "unknown"):
            raise LaneError(f"lane {lane} is already {state} ({detail}); not relaunched")
    herdr = seams.in_herdr()
    if agent is not None and not herdr:
        raise LaneError("--agent needs Herdr (HERDR_ENV and herdr); use --cmd outside it")
    if herdr and not env.get("HERDR_WORKSPACE_ID"):
        raise LaneError("HERDR_WORKSPACE_ID is unset: start lanes from a pane in the loop's workspace")
    if cmd is not None and not cmd.is_file():
        raise LaneError(f"launcher script not found: {cmd}")
    if not cwd.is_dir():
        raise LaneError(f"lane worktree not found: {cwd}")
    if herdr:
        if agent is not None and _ok(_herdr(seams, "agent", "get", label)):
            raise LaneError(f"herdr agent {label} already exists; probe it, never duplicate it")
        tabs = _herdr(seams, "tab", "list") or {}
        if any(isinstance(t, dict) and t.get("label") == label for t in tabs.get("tabs", [])):
            raise LaneError(f"herdr tab {label} already exists; probe it, never duplicate it")
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("runner.pid", "runner.rc"):  # an earlier run's files must never be read
        (out / stale).unlink(missing_ok=True)
    resume = [sys.executable, "scripts/lanes.py", "start", lane, "--cwd", str(cwd)]
    resume += ["--agent", agent] if agent is not None else ["--cmd", str(cmd)]
    resume += ["--branch", branch] if branch else []
    record: dict[str, Any] = {
        "lane": lane, "label": label, "agent": "", "tab_id": "", "pane_id": "",
        "cwd": str(cwd.resolve()), "branch": branch, "kind": agent or "cmd",
        "pid_file": str(out / "runner.pid"), "log": str(out / "runner.log"),
        "rc_file": str(out / "runner.rc"), "resume_cmd": shlex.join(resume),
        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "recorded": "",
    }  # fmt: skip
    wrapper = None
    if cmd is not None:
        wrapper = _wrapper(cmd.resolve(), cwd.resolve(), out, f"lane {lane}: {cmd}")
    if not herdr:
        assert wrapper is not None
        seams.spawn(["setsid", "-f", "nohup", "bash", str(wrapper)], cwd, out / "runner.log")
        _save(root, record)
        return record
    created = _herdr(
        seams, "tab", "create", "--workspace", env["HERDR_WORKSPACE_ID"],
        "--cwd", str(cwd), "--label", label, "--no-focus",
    )  # fmt: skip
    try:
        record["tab_id"] = str(created["tab"]["tab_id"])  # type: ignore[index]
        record["pane_id"] = str(created["root_pane"]["pane_id"])  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        raise LaneError(f"herdr tab create returned no tab/pane: {created!r}") from exc
    _save(root, record)  # saved before launching, so a failed launch still leaves a probe-able tab
    if agent is not None:
        started = _herdr(seams, "agent", "start", label, "--kind", agent, "--pane", record["pane_id"])
        if not _ok(started):
            raise LaneError(f"herdr agent start {label} failed in pane {record['pane_id']}")
        record["agent"] = label
        _save(root, record)
    elif not _ok(_herdr(seams, "pane", "run", record["pane_id"], f"bash {shlex.quote(str(wrapper))}")):
        raise LaneError(f"herdr pane run failed in pane {record['pane_id']}")
    return record


def _first_int(path: Path) -> int | None:
    try:
        words = path.read_text(encoding="utf-8").split()
        return int(words[0]) if words else None
    except (OSError, ValueError):
        return None


def probe(record: Mapping[str, Any], seams: Seams) -> tuple[str, str]:
    """``(state, detail)``: running / done / recorded / blocked / dead / unknown."""
    if record.get("recorded"):
        return "recorded", str(record["recorded"])
    rc_file = Path(str(record.get("rc_file") or ""))
    if record.get("rc_file") and rc_file.is_file():
        rc = _first_int(rc_file)
        return ("done", f"rc 0 ({rc_file})") if rc == 0 else ("blocked", f"rc {rc} ({rc_file})")
    pid_file = Path(str(record["pid_file"])) if record.get("pid_file") else None
    pid = _first_int(pid_file) if pid_file else None
    if pid is not None and pid_file and seams.pid_alive(pid, str(pid_file.parent / "live_runner.sh")):
        return "running", f"pid {pid}"
    if agent := str(record.get("agent") or ""):
        got = _herdr(seams, "agent", "get", agent) if seams.in_herdr() else None
        if got is None or got.get("_error") not in (None, "agent_not_found"):
            return "unknown", f"agent {agent}: Herdr cannot be asked; check from a Herdr pane"
        if "_error" not in got:
            status = (got.get("agent") or {}).get("agent_status") or "unknown"
            if status == "blocked":
                return "blocked", f"agent {agent} blocked (approval or question)"
            return "running", f"agent {agent} {status}; an idle agent is not a finished lane"
    gone = f"pid {pid} gone" if pid is not None else "no pid"
    return "dead", f"{gone}, no rc; resume: {record.get('resume_cmd', '')}"


def status_rows(root: Path = ROOT, seams: Seams | None = None) -> list[dict[str, Any]]:
    seams = seams or default_seams()
    rows = []
    for record in load_records(root):
        state, detail = probe(record, seams)
        rows.append({**record, "state": state, "detail": detail})
    return rows


def mark_recorded(root: Path, lane: str, note: str) -> dict[str, Any]:
    path = _record_path(root, lane)
    if not LANE_RE.fullmatch(lane) or not path.is_file():
        raise LaneError(f"no lane record for {lane!r} under {lanes_dir(root)}")
    record = json.loads(path.read_text(encoding="utf-8"))
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record["recorded"] = f"{stamp} {note}".strip()
    _save(root, record)
    return record


def carried_lines(handoff: str) -> list[str]:
    """HANDOFF.md lines that carry a lane: under a heading about carried lanes, or saying so."""
    lines, in_section = [], False
    for line in handoff.splitlines():
        if line.startswith("#"):
            in_section = bool(re.search(r"carr", line, re.I))
            continue
        if re.search(r"\bno carried\b", line, re.I):
            continue
        if in_section or re.search(r"carr(y|ies|ied)", line, re.I):
            lines.append(line)
    return lines


def _is_carried(names: Iterable[str], carried: list[str]) -> bool:
    return any(
        re.search(rf"(?<![\w/-]){re.escape(n)}(?![\w-])", line)
        for n in names
        if n
        for line in carried
    )


def _worktrees(seams: Seams) -> dict[str, str]:
    rc, out = seams.run(["git", "worktree", "list", "--porcelain"], 60)
    if rc:
        raise LaneError(f"git worktree list failed: {out[:200]}")
    trees: dict[str, str] = {}
    path = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
            trees[path] = ""
        elif line.startswith("branch ") and path:
            trees[path] = line.removeprefix("branch refs/heads/")
    return trees


def _tree_hold(path: str, branch: str, seams: Seams) -> str | None:
    """Why this lane worktree must stay (busy aside), or None when its work is finished."""
    if not branch:
        return "detached"
    rc, out = seams.run(["gh", "pr", "list", "--head", branch, "--state", "all", "--json", "state"], 60)
    if rc:
        return "unreachable"
    try:
        states = [pr["state"] for pr in json.loads(out or "[]")]
    except (json.JSONDecodeError, KeyError, TypeError):
        return "unreachable"
    if not states:
        return "no-pr"
    if "OPEN" in states:
        return "open-pr"
    rc, out = seams.run(["git", "-C", path, "status", "--porcelain"], 60)
    if rc or out:
        return "dirty"
    rc, out = seams.run(["git", "-C", path, "rev-list", "HEAD", "--not", "--remotes"], 60)
    if rc or out:
        return "unpushed"
    return None


def _inside(path: str, cwds: Iterable[str]) -> bool:
    return any(c == path or c.startswith(path + "/") for c in cwds)


def cleanup(
    *,
    root: Path = ROOT,
    prefix: str | None = None,
    go: bool = False,
    handoff: str | None = None,
    seams: Seams | None = None,
    settle: float = 2.0,
) -> list[str]:
    """Tabs first, so a finished lane's idle shell no longer pins its worktree; then worktrees."""
    seams = seams or default_seams()
    prefix = prefix or lane_prefix(root)
    if handoff is None:
        path = root / "HANDOFF.md"
        handoff = path.read_text(encoding="utf-8") if path.is_file() else ""
    carried = carried_lines(handoff)
    rows = status_rows(root, seams)
    by_cwd = {r["cwd"]: r for r in rows if r.get("cwd")}
    by_label = {r["label"]: r for r in rows if r.get("label")}

    def lane_path(path: str) -> bool:
        return path != str(root) and (path.startswith(f"{root}-") or path in by_cwd)

    def record_hold(record: Mapping[str, Any] | None) -> str | None:
        if record is None or record["state"] in RELEASABLE:
            return None
        return f"lane {record['lane']} {record['state']}"

    report: list[str] = []
    trees = _worktrees(seams)
    holds: dict[str, str | None] = {}
    for path, branch in sorted(trees.items()):
        if not lane_path(path):
            continue
        record = by_cwd.get(path)
        names = [path, Path(path).name, *((record["label"], record["lane"]) if record else ())]
        if _is_carried(names, carried):
            holds[path] = "carried"
        else:
            holds[path] = record_hold(record) or _tree_hold(path, branch, seams)

    tabs_result = _herdr(seams, "tab", "list")
    panes_result = _herdr(seams, "pane", "list") if _ok(tabs_result) else None
    if not _ok(tabs_result) or not _ok(panes_result):
        report.append("tabs skipped: herdr tab or pane list failed")
    tabs = (tabs_result or {}).get("tabs", []) if _ok(panes_result) else []
    panes = (panes_result or {}).get("panes", []) if _ok(panes_result) else []
    freed: set[str] = set()
    for meta in tabs:
        label, tab_id = str(meta.get("label", "")), str(meta.get("tab_id", ""))
        if not label.startswith(prefix) or PROTECTED.search(label):
            continue
        mine = [p for p in panes if p.get("tab_id") == tab_id]
        raw = [str(p.get("cwd") or "") for p in mine]
        paths = {c.removesuffix(DELETED) for c in raw}
        statuses = {p.get("agent_status") for p in mine}
        record = by_label.get(label)
        if statuses - SETTLED:
            hold = "active: " + ",".join(sorted(str(s) for s in statuses - SETTLED))
        elif _is_carried([label, *paths, *((record["lane"],) if record else ())], carried):
            hold = "carried"
        elif hold := record_hold(record):
            pass
        elif not paths or not all(
            lane_path(c.removesuffix(DELETED)) and (c.endswith(DELETED) or c in trees) for c in raw
        ):
            hold = "foreign"  # only a registered lane worktree, or one already deleted
        elif any(p in trees and holds.get(p) for p in paths):
            hold = "worktree-kept"
        else:
            hold = None
        if hold == "carried":  # a lane carried by its tab name keeps its worktree too
            holds.update({p: "carried" for p in paths if p in holds})
        if hold:
            report.append(f"hold tab {tab_id} {label}: {hold}")
        elif not go:
            report.append(f"would close tab {tab_id} {label}")
            freed |= paths
        elif _ok(_herdr(seams, "tab", "close", tab_id)):
            report.append(f"closed tab {tab_id} {label}")
            freed |= paths
        else:
            report.append(f"hold tab {tab_id} {label}: close failed")

    if go and freed and settle:
        time.sleep(settle)  # let the closed tabs' shells exit
    cwds = seams.cwds()  # re-read: closing a tab ends its shell
    if cwds is not None and not go:  # a dry run cannot close tabs, so it assumes their shells go
        cwds = [c for c in cwds if not any(_inside(f, [c]) for f in freed)]
    removed = False
    for path, hold in holds.items():
        branch = trees[path] or "detached"
        if not hold:
            hold = "busy-unknown" if cwds is None else ("busy" if _inside(path, cwds) else None)
        if hold:
            report.append(f"hold {path} ({branch}): {hold}")
        elif not go:
            report.append(f"would remove {path} ({branch})")
        else:
            rc, out = seams.run(["git", "worktree", "remove", path], 120)
            if rc:
                report.append(f"hold {path} ({branch}): remove failed: {out[:160]}")
            else:
                report.append(f"removed {path} ({branch})")
                removed = True
    if removed:
        seams.run(["git", "worktree", "prune"], 60)
    return report or ["no lanes to release"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    start_p = sub.add_parser("start", help="start a lane that outlives this session")
    start_p.add_argument("lane")
    start_p.add_argument("--cwd", type=Path, required=True, help="the lane worktree")
    how = start_p.add_mutually_exclusive_group(required=True)
    how.add_argument("--cmd", type=Path, help="launcher script, run under the pid/log/rc wrapper")
    how.add_argument("--agent", help="Herdr agent kind, e.g. claude or codex")
    start_p.add_argument("--branch", default="", help="the lane's branch, for the record")
    status_p = sub.add_parser("status", help="probe every recorded lane")
    status_p.add_argument("--json", action="store_true")
    rec_p = sub.add_parser("recorded", help="mark a finished lane as written up")
    rec_p.add_argument("lane")
    rec_p.add_argument("--note", default="")
    clean_p = sub.add_parser("cleanup", help="release finished lanes; a dry run unless --go")
    clean_p.add_argument("--go", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "start":
            record = start(args.lane, cwd=args.cwd, cmd=args.cmd, agent=args.agent, branch=args.branch)
            print(f"started {record['label']} in {record['cwd']}")
            if record["agent"]:
                print(f'next: herdr agent prompt {record["agent"]} "<the lane\'s full task>"')
        elif args.action == "status":
            rows = status_rows()
            if args.json:
                print(json.dumps(rows, indent=2))
            for row in [] if args.json else rows:
                print(f"{row['label']}  {row['state']}  {row['detail']}")
            if not rows and not args.json:
                print(f"no lanes recorded under {lanes_dir(ROOT)}")
        elif args.action == "recorded":
            print(f"recorded {mark_recorded(ROOT, args.lane, args.note)['label']}")
        else:
            for line in cleanup(go=args.go):
                print(line)
    except LaneError as exc:
        print(f"lanes.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
