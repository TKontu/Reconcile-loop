#!/usr/bin/env python3
"""Run the plan/execute/review/merge/reconcile/handoff loop, one fresh Claude session per round.

Optional add-on: the core workflow never depends on it. Needs POSIX, Herdr, Claude Code and an
authenticated `gh`. See .agent/supervisor.md.

A plain process (no LLM) in its own Herdr pane. Each round gets a new ``claude`` process with a
supervisor-chosen session id, so "cleared" holds by construction. Completion is an explicit,
validated sentinel, never Herdr's ``idle``: an orchestrator waiting on CI is idle too.

Live lanes carry over untouched: they run in their own ``live-<repo>-<lane>`` Herdr tabs, and the only tab
this process ever closes is the one it created for the round's orchestrator.

Watchdog: transcript silence or no outward progress (main, PR heads, round manifests) earns a
nudge; only outward progress refunds nudges, so a heartbeat that merely keeps the transcript
growing cannot wait forever. Exhausted nudges recycle the session; repeated recycles halt.

    up [--for 8h] | watch | run [--dry-run] | status | stop-after-round | stop-in 8h | stop
    clear-halt | complete --outcome ... | note --kind ... --text ...
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import fcntl
import json
import os
import re
import select
import shutil
import subprocess
import sys
import termios
import textwrap
import time
import tomllib
import tty
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("ROUND_SUPERVISOR_ROOT", Path(__file__).resolve().parents[1]))
STATE = ROOT / ".agent-runs" / "supervisor"  # .agent-runs/ is already gitignored by bootstrap


def project_config(root: Path = ROOT) -> dict[str, Any]:
    """`.agent/config.toml`, or {} when absent or unreadable (defaults apply)."""
    try:
        return tomllib.loads((root / ".agent" / "config.toml").read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def repo_names(root: Path, config: dict[str, Any]) -> dict[str, str]:
    """Herdr agent names are global across projects, so every name carries this repo's slug.

    The slug is `[supervisor] name` from .agent/config.toml, else the checkout's directory name.
    """
    raw = str(config.get("supervisor", {}).get("name") or root.name)
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-") or "repo"
    return {
        "slug": slug,
        "agent": f"round-planner-{slug}",
        "loop_tab": f"round-loop-{slug}",
        "lane_prefix": f"live-{slug}-",
    }


CONFIG = project_config()
NAMES = repo_names(ROOT, CONFIG)
AGENT = NAMES["agent"]
TAB_LABEL = NAMES["agent"]
LANE_PREFIX = NAMES["lane_prefix"]
BRANCH = CONFIG.get("project", {}).get("default_branch", "main")
# Unattended sessions cannot answer approval dialogs; `auto` lets the round run. Set
# [supervisor] permission_mode in .agent/config.toml to choose another mode.
PERMISSION_ARGS = (
    "--permission-mode", CONFIG.get("supervisor", {}).get("permission_mode", "auto"),
)  # fmt: skip
PROJECT_LOGS = Path.home() / ".claude" / "projects" / re.sub(r"[/.]", "-", str(ROOT))
LIMIT_RE = re.compile(r"usage limit|limit reached|out of (extra )?usage|rate.limited", re.I)
SELF = Path(__file__).resolve()

ROUND_PROMPT = """You are the orchestrator of supervised round {round}, in a fresh session.
Run /takeoff (.agent/commands/takeoff.md) for orientation, then (overriding its "stop") run exactly
one full round: /plan-round, /execute-task in isolated lanes, /review-round, fix simple findings or
dispatch fixers, /merge-round, /reconcile, /handoff. Keep the round ledger with
python3 scripts/round.py throughout. Decide routine choices as recommended; record significant
decisions in HANDOFF.md.
- Merge only within the merge authority in .agent/config.toml. If that authority is not yours,
  park approved PRs in HANDOFF.md as owed to the operator and open a dashboard item for them.
- Before planning new work, take over every finished lane HANDOFF.md names (check its Herdr
  agent, its result under .agent-runs/ and its PR; an idle agent is not a finished lane). Record
  it if it is not recorded yet. Lanes still running stay carried.
- Live or long work runs only as Herdr lanes, each agent and tab named {lane_prefix}<lane> (Herdr
  names are global across projects, so always use this prefix). A lane is a tab in this round's
  workspace (herdr tab create --workspace "$HERDR_WORKSPACE_ID"); never create a Herdr workspace. Never wait for one to
  finish: carry it in HANDOFF.md and end the round. Probe before starting; never duplicate.
  Never halt, relaunch or take over a carried lane; each continues across rounds until it completes.
- HANDOFF.md must name every carried lane: its tab, owner, what it is doing, how to check it, and
  that it carries over and must not be halted or duplicated.
- While waiting on CI or subagents, keep a background wake-up armed so the session resumes.
- A blocked critical path is not a halt: plan other lanes.
- Report news for the operator's dashboard, plain language, one line, only what they would want to
  know: python3 {script} note --kind KIND --text "..." --ref "<record>"
  KIND: result (a significant outcome), issue (a significant obstacle), decision (a significant one
  you made), open (a decision owed by the operator; --ref is required, and note --close REF when
  it is settled). A problem states its cause. Expect a handful per round, not a diary. At each
  phase change also run: note --kind stage --text "<phase>".
- Your very last action, after every subagent has finished and handoff has validated:
    python3 {script} complete --outcome continue
  Only for a reached goal, an operator instruction or an obstacle blocking all future lanes, use
  --outcome halt --reason "<why>" instead. Then end your turn; a new session takes the next round.
"""
SILENT_NUDGE = (
    "Supervisor: this session has been silent for {minutes} minutes and round {round} is not "
    "complete. Re-check every pending subagent, PR and CI state directly, act on what you find, "
    "arm a heartbeat. If nothing is left, run handoff and the complete command."
)
PROGRESS_NUDGE = (
    "Supervisor: no outward progress (main, PR heads, round manifests) for {minutes} minutes. "
    "Name what the round is waiting on and unblock it. Do not wait on live lanes: carry them. If "
    "this round cannot advance, run reconcile and handoff, then the complete command."
)
DENIED_NUDGE = (
    "Supervisor: the approval dialog went unanswered, so that action was refused. Do it another "
    "way, or park it in HANDOFF.md as owed to the operator, and continue the round."
)


@dataclass(frozen=True)
class Config:
    poll_s: int = 60
    fingerprint_s: int = 300
    silence_s: int = 45 * 60  # above the 25-minute heartbeat
    no_progress_s: int = 3 * 3600
    nudge_gap_s: int = 45 * 60
    blocked_s: int = 30 * 60
    settle_s: int = 10 * 60
    round_cap_s: int = 12 * 3600
    limit_max_s: int = 6 * 3600
    max_nudges: int = 3
    max_recycles: int = 2
    max_no_advance: int = 3
    gap_s: int = 60


@dataclass
class Tracker:
    """Per-round watchdog memory, plus the across-round breaker counters."""

    round: int = 0
    started: float = 0.0
    last_progress: float = 0.0
    last_nudge: float = 0.0
    nudges: int = 0
    blocked_since: float | None = None
    done_since: float | None = None
    limited_since: float | None = None
    recycles: int = 0
    no_advance: int = 0
    main_at_start: str = ""


@dataclass(frozen=True)
class Observation:
    now: float
    status: str | None  # Herdr agent_status; None = the agent is gone
    sentinel: dict[str, Any] | None  # already matched to this round
    activity: float  # newest transcript write, subagents included
    limited: bool = False
    stop_now: bool = False
    stop_after_round: bool = False


@dataclass(frozen=True)
class Action:
    kind: str  # wait|nudge_silent|nudge_progress|deny|next|recycle|halt
    reason: str = ""


def decide(cfg: Config, t: Tracker, o: Observation) -> Action:
    """The whole policy; mutates only the tracker's timers."""
    if o.stop_now:
        return Action("halt", "operator stop")
    if o.sentinel is not None:
        if o.status == "working":
            t.done_since = t.done_since or o.now
            if o.now - t.done_since < cfg.settle_s:
                return Action("wait", "sentinel written; agent settling")
        if o.sentinel.get("outcome") == "halt":
            return Action("halt", f"round asked to halt: {o.sentinel.get('reason', '')}")
        if o.stop_after_round:
            return Action("halt", "operator stop after round")
        return Action("next", "round complete")
    if o.status is None:
        return Action("recycle", "agent is gone without completing the round")

    if o.status == "blocked":
        t.blocked_since = t.blocked_since or o.now
        if o.now - t.blocked_since >= cfg.blocked_s:
            t.blocked_since = None
            return Action("deny", "approval dialog timed out")
        return Action("wait", "blocked on a dialog")
    t.blocked_since = None

    if o.limited:
        t.limited_since = t.limited_since or o.now
        if o.now - t.limited_since < cfg.limit_max_s:
            return Action("wait", "usage limit")
    else:
        t.limited_since = None

    if o.now - t.started >= cfg.round_cap_s:
        return Action("recycle", "round exceeded its time cap")

    silent = o.now - max(o.activity, t.last_nudge, t.started) >= cfg.silence_s
    stuck = o.now - t.last_progress >= cfg.no_progress_s
    if not (silent or stuck):
        return Action("wait")
    if o.now - t.last_nudge < cfg.nudge_gap_s:
        return Action("wait", "nudge spacing")
    if t.nudges >= cfg.max_nudges:
        return Action("recycle", f"{t.nudges} nudges without outward progress")
    return Action("nudge_silent" if silent else "nudge_progress")


def after_round(cfg: Config, t: Tracker, *, recycled: bool, main_sha: str) -> Action | None:
    """Circuit breaker between rounds: halt rather than burn sessions on no effect."""
    advanced = bool(main_sha) and main_sha != t.main_at_start
    t.no_advance = 0 if advanced else t.no_advance + 1
    t.recycles = t.recycles + 1 if recycled else 0
    if t.recycles >= cfg.max_recycles:
        return Action("halt", f"{t.recycles} consecutive recycled rounds")
    if t.no_advance >= cfg.max_no_advance:
        return Action("halt", f"main unchanged across {t.no_advance} rounds")
    return None


Run = Callable[[Sequence[str], float], tuple[int, str]]
NOTE_MAX = 140
FEED_KINDS = ("result", "issue", "decision", "open", "round", "watchdog", "halt")
ICONS = {
    "result": ("✔", "32"),
    "issue": ("⚠", "31"),
    "decision": ("◆", "36"),
    "open": ("?", "35"),
    "round": ("↻", "2"),
    "watchdog": ("⏱", "33"),
    "halt": ("■", "31"),
}


def _run(cmd: Sequence[str], timeout: float = 90) -> tuple[int, str]:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return done.returncode, done.stdout + done.stderr


def _dump(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    tmp.replace(path)


def _load(path: Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def log(message: str) -> None:
    line = f"{time.strftime('%FT%TZ', time.gmtime())} {message}"
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "supervisor.log").open("a") as fh:
        fh.write(line + "\n")
    with contextlib.suppress(OSError):  # a closed terminal must not take the supervisor down
        print(line, flush=True)


def own_workspace() -> list[str]:
    """`--workspace <id>` for the supervisor's own Herdr workspace.

    Without it `tab create` uses whichever workspace is focused, so a planner could open in another
    repo's workspace. preflight refuses to run without HERDR_WORKSPACE_ID.
    """
    workspace = os.environ.get("HERDR_WORKSPACE_ID", "")
    return ["--workspace", workspace] if workspace else []


class Herdr:
    def __init__(self, run: Run = _run) -> None:
        self.run = run

    def _json(self, *args: str, timeout: float = 90) -> dict[str, Any]:
        rc, out = self.run(["herdr", *args], timeout)
        if rc:
            raise RuntimeError(f"herdr {' '.join(args)}: {out[:300]}")
        result: dict[str, Any] = json.loads(out)["result"]
        return result

    def agents(self) -> list[dict[str, Any]]:
        agents: list[dict[str, Any]] = self._json("agent", "list")["agents"]
        return agents

    def agent(self, name: str = AGENT) -> dict[str, Any] | None:
        return next((a for a in self.agents() if a.get("name") == name), None)

    def new_tab(self) -> tuple[str, str]:
        made = self._json(
            "tab", "create", *own_workspace(), "--cwd", str(ROOT), "--label", TAB_LABEL, "--no-focus",
            "--env", f"ROUND_SUPERVISOR_ROOT={ROOT}",
        )  # fmt: skip
        return made["tab"]["tab_id"], made["root_pane"]["pane_id"]

    def start(self, pane: str, session: str, round_no: int, extra: Sequence[str]) -> None:
        self._json(
            "agent", "start", AGENT, "--kind", "claude", "--pane", pane, "--timeout", "120000",
            "--", "--session-id", session, "-n", f"round-{round_no}", *extra,
            timeout=150,
        )  # fmt: skip

    def prompt(self, text: str) -> tuple[int, str]:
        return self.run(["herdr", "agent", "prompt", AGENT, text], 60)

    def keys(self, *keys: str) -> None:
        self.run(["herdr", "agent", "send-keys", AGENT, *keys], 30)

    def screen(self) -> str:
        return self.run(["herdr", "agent", "read", AGENT, "--source", "visible"], 30)[1]

    def close_tab(self, tab: str) -> None:
        self.run(["herdr", "tab", "close", tab], 30)

    def notify(self, title: str, body: str) -> None:
        self.run(["herdr", "notification", "show", title, "--body", body, "--sound", "request"], 30)


def main_sha(run: Run = _run) -> str:
    rc, out = run(["git", "ls-remote", "origin", f"refs/heads/{BRANCH}"], 60)
    return out.split()[0] if rc == 0 and out.strip() else ""


def fingerprint(run: Run = _run) -> str | None:
    """Outward state of the project; None when a probe failed (never counts as a change)."""
    sha = main_sha(run)
    rc, prs = run(["gh", "pr", "list", "--json", "number,headRefOid"], 60)
    if not sha or rc:
        return None
    manifests = sorted(
        f"{p}:{p.stat().st_mtime_ns}" for p in (ROOT / ".agent-runs").glob("*/round.json")
    )
    return json.dumps([sha, sorted(prs.split()), manifests])


def newest_activity(session: str, floor: float) -> float:
    base = PROJECT_LOGS
    paths = [base / f"{session}.jsonl", *(base / session / "subagents").glob("**/*.jsonl")]
    return max([floor, *(p.stat().st_mtime for p in paths if p.exists())])


def read_sentinel(round_no: int) -> dict[str, Any] | None:
    data = _load(STATE / "complete.json")
    return data if data and data.get("round") == round_no else None


class Supervisor:
    def __init__(
        self,
        cfg: Config,
        extra: Sequence[str],
        herdr: Herdr | None = None,
        prompt: str = ROUND_PROMPT,
    ) -> None:
        self.prompt = prompt
        self.cfg, self.extra, self.herdr = cfg, (*PERMISSION_ARGS, *extra), herdr or Herdr()
        self.t = Tracker()
        self.tab = ""
        self.session = ""
        self.print_last = ""
        self.fp: str | None = None
        self.fp_at = 0.0

    def preflight(self, *, allow_other: bool) -> None:
        if os.environ.get("HERDR_ENV") != "1":
            sys.exit("refusing: not inside a Herdr pane")
        if not os.environ.get("HERDR_WORKSPACE_ID"):
            sys.exit("refusing: HERDR_WORKSPACE_ID unset; planner tabs must open in this workspace")
        if (STATE / "HALT").exists():
            sys.exit(f"refusing: {STATE / 'HALT'} exists; see `status`, then `clear-halt`")
        others = [
            a.get("name") or a.get("pane_id")
            for a in self.herdr.agents()
            if a.get("agent") == "claude"
            and a.get("cwd") == str(ROOT)
            and a.get("name") != AGENT
            and a.get("pane_id") != os.environ.get("HERDR_PANE_ID")
            and a.get("agent_status") == "working"
        ]
        if others and not allow_other:
            sys.exit(f"refusing: other Claude sessions are working in {ROOT}: {others}")

    def begin_round(self, round_no: int) -> None:
        (STATE / "complete.json").unlink(missing_ok=True)
        self.session = str(uuid.uuid4())
        self.tab, pane = self.herdr.new_tab()
        now = time.time()
        sha = main_sha(self.herdr.run)
        _dump(
            STATE / "current.json",
            {"round": round_no, "session": self.session, "tab": self.tab, "started": now,
             "main_at_start": sha},
        )  # fmt: skip
        keep = dataclasses.asdict(self.t)
        keep.update(
            round=round_no, started=now, last_progress=now, last_nudge=0.0, nudges=0,
            blocked_since=None, done_since=None, limited_since=None, main_at_start=sha,
        )  # fmt: skip
        self.t = Tracker(**keep)
        time.sleep(2)  # the new tab's shell must reach its prompt
        self.herdr.start(pane, self.session, round_no, self.extra)
        rc, out = self.herdr.prompt(self.prompt.format(round=round_no, script=SELF, lane_prefix=LANE_PREFIX))
        if rc:
            raise RuntimeError(f"round prompt refused: {out[:300]}")
        news("round", f"Round {round_no} started")
        log(f"round {round_no} started session={self.session} tab={self.tab} main={sha[:8]}")

    def adopt(self) -> bool:
        """A restarted supervisor resumes the live round instead of duplicating it."""
        cur = _load(STATE / "current.json")
        agent = self.herdr.agent()
        if not cur or agent is None:
            return False
        if agent.get("cwd") not in (None, str(ROOT)):
            sys.exit(f"refusing: agent {AGENT} belongs to {agent.get('cwd')}; set [supervisor] name")
        self.session, self.tab = cur["session"], cur["tab"]
        now = time.time()
        self.t = Tracker(round=cur["round"], started=cur["started"], last_progress=now,
                         main_at_start=cur.get("main_at_start", ""))  # fmt: skip
        log(f"adopted round {cur['round']} session={self.session}")
        return True

    def end_session(self) -> None:
        """Exit gracefully so the transcript flushes; then close only the tab we created."""
        if self.herdr.agent() is not None:
            self.herdr.keys("esc")
            time.sleep(3)
            self.herdr.prompt("/exit")
            deadline = time.time() + 60
            while time.time() < deadline and self.herdr.agent() is not None:
                time.sleep(3)
        if self.tab:
            self.herdr.close_tab(self.tab)

    def observe(self, now: float) -> Observation:
        agent = self.herdr.agent()
        status = agent.get("agent_status") if agent else None
        activity = newest_activity(self.session, self.t.started)
        limited = (
            status is not None
            and now - activity >= self.cfg.poll_s * 5
            and bool(LIMIT_RE.search(self.herdr.screen()))
        )
        return Observation(
            now=now,
            status=status,
            sentinel=read_sentinel(self.t.round),
            activity=activity,
            limited=limited,
            stop_now=(STATE / "STOP").exists(),
            stop_after_round=stop_requested(),
        )

    def refresh_progress(self, now: float) -> None:
        if now - self.fp_at < self.cfg.fingerprint_s:
            return
        self.fp_at = now
        new = fingerprint(self.herdr.run)
        if new is None:
            return
        if self.fp is not None and new != self.fp:
            self.t.last_progress, self.t.nudges = now, 0
            log("outward progress")
        self.fp = new

    def halt(self, reason: str) -> None:
        _dump(STATE / "HALT", {"reason": reason, "round": self.t.round, "at": time.time()})
        log(f"HALT: {reason}")
        news("halt", reason)
        self.herdr.notify(f"Round loop {NAMES['slug']} halted", reason[:200])

    def step(self) -> bool:
        """One poll; False ends the supervisor."""
        now = time.time()
        self.refresh_progress(now)
        action = decide(self.cfg, self.t, self.observe(now))
        if action.kind != "wait" or action.reason != self.print_last:
            log(f"round {self.t.round}: {action.kind} {action.reason}")
            self.print_last = action.reason
        minutes = int((now - self.t.last_progress) // 60)
        if action.kind in ("nudge_silent", "nudge_progress"):
            quiet = int((now - newest_activity(self.session, self.t.started)) // 60)
            text = SILENT_NUDGE if action.kind == "nudge_silent" else PROGRESS_NUDGE
            self.herdr.prompt(text.format(minutes=quiet or minutes, round=self.t.round))
            self.t.nudges += 1
            news("watchdog", f"Nudged the planner: {action.kind.removeprefix('nudge_')}")
            self.t.last_nudge = now
        elif action.kind == "deny":
            self.herdr.notify(f"Round loop {NAMES['slug']}: dialog timed out", f"round {self.t.round}")
            news("watchdog", "An unanswered approval dialog was refused")
            self.herdr.keys("esc")
            time.sleep(2)
            self.herdr.prompt(DENIED_NUDGE)
            self.t.last_nudge = now
        elif action.kind == "halt":
            self.halt(action.reason)
            return False
        elif action.kind in ("next", "recycle"):
            if action.kind == "recycle":
                news("watchdog", f"Replaced the planner session: {action.reason}")
            self.end_session()
            sha = main_sha(self.herdr.run)
            stop = after_round(self.cfg, self.t, recycled=action.kind == "recycle", main_sha=sha)
            if stop:
                self.halt(stop.reason)
                return False
            if stop_requested():
                self.halt("operator stop after round")
                return False
            time.sleep(self.cfg.gap_s)
            self.begin_round(self.t.round + 1)
        return True

    def run(self, *, allow_other: bool) -> None:
        self.preflight(allow_other=allow_other)
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / "lock").open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                sys.exit("refusing: another supervisor holds the lock")
            if not self.adopt():
                self.begin_round(self.t.round + 1)
            while True:
                try:
                    if not self.step():
                        return
                except Exception as exc:  # a probe hiccup must not orphan the round
                    log(f"tick error: {exc!r}")
                time.sleep(self.cfg.poll_s)


def stop_requested(now: float | None = None) -> bool:
    if (STATE / "STOP_AFTER_ROUND").exists():
        return True
    deadline = _load(STATE / "deadline.json")
    return deadline is not None and (now or time.time()) >= deadline["at"]


def parse_duration(text: str) -> int:
    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?", text)
    if not match or not text:
        raise ValueError(f"not a duration like 8h or 90m: {text}")
    return int(match[1] or 0) * 3600 + int(match[2] or 0) * 60


def set_deadline(duration: str) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    _dump(STATE / "deadline.json", {"at": time.time() + parse_duration(duration)})


def news(kind: str, text: str, ref: str = "") -> None:
    cur = _load(STATE / "current.json") or {}
    entry = {"at": time.time(), "round": cur.get("round"), "kind": kind, "text": text, "ref": ref}
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "news.jsonl").open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def read_news() -> list[dict[str, Any]]:
    try:
        lines = (STATE / "news.jsonl").read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        with contextlib.suppress(ValueError):
            out.append(json.loads(line))
    return out


def note(kind: str | None, text: str, ref: str, close: str) -> int:
    """The orchestrator's channel to the dashboard; refuses anything that is not a TL;DR."""
    if close:
        news("closed", "", close)
        return 0
    if not kind or not text:
        print("note needs --kind and --text, or --close", file=sys.stderr)
        return 2
    if len(text) > NOTE_MAX:
        print(f"{len(text)} characters; shorten to {NOTE_MAX}, link the rest", file=sys.stderr)
        return 2
    if kind == "open" and not ref:
        print("--kind open needs --ref, so it can be closed later", file=sys.stderr)
        return 2
    news(kind, text, ref)
    return 0


def _age(seconds: float) -> str:
    minutes = int(seconds // 60)
    return f"{minutes // 60}h{minutes % 60:02d}m" if minutes >= 60 else f"{minutes}m"


def _supervisor_alive() -> bool:
    try:
        with (STATE / "lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True
    return False


def open_items(events: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["kind"] == "open":
            items[event["ref"]] = event
        elif event["kind"] == "closed":
            items.pop(event["ref"], None)
    return list(items.values())


def phase_of(*, halt: dict[str, Any] | None, alive: bool, stopping: bool) -> tuple[str, str]:
    if halt:
        return "HALTED", str(halt.get("reason", ""))
    if not alive:
        return "SUPERVISOR DOWN", "nothing is guarding the round"
    return ("STOPPING", "after this round") if stopping else ("RUNNING", "")


def _paint(text: str, code: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m"


def _entry(event: dict[str, Any], now: float, width: int) -> list[str]:
    icon, code = ICONS[event["kind"]]
    head = f"{_age(now - event['at']):>6}  r{event.get('round') or '-':<3} "
    text = event["text"] + (f"  [{event['ref']}]" if event.get("ref") else "")
    body = textwrap.wrap(text, max(width - len(head) - 3, 20)) or [""]
    first = _paint(head, "2") + _paint(icon, code) + "  " + body[0]
    return [first, *(" " * (len(head) + 3) + line for line in body[1:])]


def render(view: dict[str, Any], width: int, rows: int, offset: int) -> list[str]:
    """Fixed status at the top; the news below scrolls. Pure, so it is testable."""
    now, events = view["now"], view["news"]
    phase, detail = view["phase"]
    code = {"RUNNING": "1;32", "STOPPING": "1;33"}.get(phase, "1;31")
    facts = [
        f"round {view['round'] or '-'}",
        _age(now - view["started"]) if view["started"] else "",
    ]
    stage = next((e["text"] for e in reversed(events) if e["kind"] == "stage"), "")
    if stage:
        facts.append(stage)
    if view["deadline"]:
        left = view["deadline"] - now
        facts.append(f"time limit in {_age(left)}" if left > 0 else "time limit reached")
    top = [
        _paint(f" {phase} ", code + ";7") + "  " + "  ·  ".join(f for f in facts if f),
    ]
    if detail:
        top.append(_paint(detail, "2"))
    rule = _paint("─" * width, "2")
    opens = open_items(events)
    top += [rule, _paint(f"OWED BY YOU ({len(opens)})", "1;35")]
    top += [line for item in opens[-5:] for line in _entry(item, now, width)] or [
        _paint("none", "2")
    ]
    lanes = "   ".join(f"{name} {state}" for name, state in view["lanes"]) or "none"
    top += [rule, _paint("LANES ", "1") + _paint("(agent state, not lane state)", "2")]
    top += textwrap.wrap(lanes, width) or []
    top += [rule, _paint("NEWS ", "1") + _paint("newest first", "2")]
    feed = [
        line
        for event in reversed(events)
        if event["kind"] in FEED_KINDS
        for line in _entry(event, now, width)
    ]
    room = max(rows - len(top) - 1, 3)
    offset = min(offset, max(len(feed) - room, 0))
    shown = feed[offset : offset + room]
    keys = (
        f"j/k scroll ({offset + len(shown)}/{len(feed)})   s stop after round on/off   q quit view"
    )
    return [*top, *shown, *[""] * (room - len(shown)), _paint(keys, "2")]


def gather_view(herdr: Herdr) -> dict[str, Any]:
    cur = _load(STATE / "current.json") or {}
    try:
        lanes = [
            (a["name"], a.get("agent_status", "?"))
            for a in herdr.agents()
            if str(a.get("name", "")).startswith(LANE_PREFIX)
        ]
    except (RuntimeError, ValueError):
        lanes = []
    halt = _load(STATE / "HALT")
    return {
        "now": time.time(),
        "phase": phase_of(halt=halt, alive=_supervisor_alive(), stopping=stop_requested()),
        "round": cur.get("round"),
        "started": cur.get("started"),
        "deadline": (_load(STATE / "deadline.json") or {}).get("at"),
        "lanes": lanes,
        "news": read_news(),
    }


def watch(refresh_s: float = 3.0) -> int:
    """The operator's dashboard; closing it never affects the loop."""
    herdr, offset, fd = Herdr(), 0, sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    sys.stdout.write("\x1b[?1049h\x1b[?25l")
    try:
        while True:
            size = shutil.get_terminal_size()
            lines = render(gather_view(herdr), size.columns, size.lines, offset)
            sys.stdout.write("\x1b[H\x1b[J" + "\n".join(lines))
            sys.stdout.flush()
            if not select.select([fd], [], [], refresh_s)[0]:
                continue
            key = os.read(fd, 1).decode(errors="ignore")
            if key == "q":
                return 0
            if key == "j":
                offset += 3
            elif key == "k":
                offset = max(offset - 3, 0)
            elif key == "s":
                flag = STATE / "STOP_AFTER_ROUND"
                if flag.exists():
                    flag.unlink()
                else:
                    STATE.mkdir(parents=True, exist_ok=True)
                    flag.touch()
    finally:
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def up(run_args: Sequence[str], herdr: Herdr | None = None) -> int:
    """One command: a round-loop tab with the supervisor on top and the dashboard below."""
    herdr = herdr or Herdr()
    me = f"python3 {SELF}"
    made = herdr._json(
        "tab", "create", *own_workspace(), "--cwd", str(ROOT), "--label", NAMES["loop_tab"],
        "--no-focus",
        "--env", f"ROUND_SUPERVISOR_ROOT={ROOT}",
    )  # fmt: skip
    top = made["root_pane"]["pane_id"]
    split = herdr._json(
        "pane", "split", top, "--direction", "down", "--ratio", "0.25", "--cwd", str(ROOT),
        "--env", f"ROUND_SUPERVISOR_ROOT={ROOT}", "--no-focus",
    )  # fmt: skip
    time.sleep(2)  # both shells must reach their prompts
    herdr.run(["herdr", "pane", "run", top, " ".join([me, "run", *run_args])], 30)
    herdr.run(["herdr", "pane", "run", split["pane"]["pane_id"], f"{me} watch"], 30)
    print(f"started in tab {made['tab']['tab_id']}")
    return 0


def complete(outcome: str, reason: str, run: Run = _run) -> int:
    """Called by the orchestrator as its last action; refuses an unfinished handoff."""
    cur = _load(STATE / "current.json")
    if cur is None:
        print("no supervised round is open", file=sys.stderr)
        return 2
    handoff = ROOT / "HANDOFF.md"
    if not handoff.exists() or handoff.stat().st_mtime < cur["started"]:
        print("HANDOFF.md was not written this round; run handoff first", file=sys.stderr)
        return 1
    rc, out = run(
        [sys.executable, str(SELF.parent / "round.py"), "check-handoff", str(handoff)], 120
    )
    if rc:
        print(f"HANDOFF.md is invalid:\n{out}", file=sys.stderr)
        return 1
    if outcome == "halt" and not reason:
        print("--outcome halt needs --reason", file=sys.stderr)
        return 2
    payload = {"round": cur["round"], "outcome": outcome, "reason": reason, "at": time.time()}
    _dump(STATE / "complete.json", payload)
    news("round", f"Round {cur['round']} complete" + (f": halt, {reason}" if reason else ""))
    print(f"round {cur['round']} recorded complete ({outcome}); end your turn")
    return 0


def status() -> int:
    print("names:", NAMES)
    print("current:", _load(STATE / "current.json"))
    print("complete:", _load(STATE / "complete.json"))
    print("halt:", _load(STATE / "HALT"))
    for flag in ("STOP", "STOP_AFTER_ROUND"):
        print(f"{flag}:", (STATE / flag).exists())
    return 0


def dry_run(cfg: Config) -> int:
    """Show the policy and the read-only preconditions; start and change nothing."""
    print(f"root={ROOT}\nstate={STATE}\ntranscripts={PROJECT_LOGS} exists={PROJECT_LOGS.is_dir()}")
    print(f"config={dataclasses.asdict(cfg)}")
    print(f"claude args={PERMISSION_ARGS}")
    agents = Herdr().agents()
    print("named agents:", [a.get("name") for a in agents if a.get("name")])
    holder = next((a for a in agents if a.get("name") == AGENT), None)
    print(f"names={NAMES}")
    print(f"name {AGENT} in use:", holder is not None, f"(cwd {holder.get('cwd')})" if holder else "")
    print("HALT present:", (STATE / "HALT").exists())
    print("fingerprint ok:", fingerprint() is not None)
    print("first prompt:\n" + ROUND_PROMPT.format(round=1, script=SELF, lane_prefix=LANE_PREFIX))
    return 0


def with_overrides(cfg: Config, pairs: Sequence[str]) -> Config:
    """Apply KEY=INT overrides (shortened timers for a trial); unknown keys are an error."""
    changes = {key: int(value) for key, _, value in (pair.partition("=") for pair in pairs)}
    return dataclasses.replace(cfg, **changes)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--dry-run", action="store_true")
    run_p.add_argument("--allow-other", action="store_true")
    run_p.add_argument("--claude-arg", action="append", default=[])
    run_p.add_argument("--prompt-file", type=Path, help="trial only: replaces the round prompt")
    run_p.add_argument("--set", action="append", default=[], metavar="KEY=SECONDS")
    for name in ("status", "stop-after-round", "stop", "clear-halt", "watch"):
        sub.add_parser(name)
    sub.add_parser("stop-in").add_argument("duration")
    up_p = sub.add_parser("up")
    up_p.add_argument("--for", dest="limit", help="finish the current round, then stop: 8h, 90m")
    up_p.add_argument("--prompt-file")
    up_p.add_argument("--allow-other", action="store_true")
    up_p.add_argument("--set", action="append", default=[], metavar="KEY=SECONDS")
    note_p = sub.add_parser("note")
    note_p.add_argument("--kind", choices=(*FEED_KINDS[:4], "stage"))
    note_p.add_argument("--text", default="")
    note_p.add_argument("--ref", default="")
    note_p.add_argument("--close", default="")
    done_p = sub.add_parser("complete")
    done_p.add_argument("--outcome", choices=("continue", "halt"), required=True)
    done_p.add_argument("--reason", default="")
    args = parser.parse_args(argv)

    if args.cmd == "note":
        return note(args.kind, args.text, args.ref, args.close)
    if args.cmd == "watch":
        return watch()
    if args.cmd == "stop-in":
        set_deadline(args.duration)
        return 0
    if args.cmd == "up":
        if args.limit:
            set_deadline(args.limit)
        extra = [f"--set={item}" for item in args.set]
        extra += ["--allow-other"] if args.allow_other else []
        return up([*extra, *([f"--prompt-file={args.prompt_file}"] if args.prompt_file else [])])
    cfg = Config()
    if args.cmd == "run":
        cfg = with_overrides(cfg, args.set)
        if args.dry_run:
            return dry_run(cfg)
        prompt = args.prompt_file.read_text() if args.prompt_file else ROUND_PROMPT
        Supervisor(cfg, args.claude_arg, prompt=prompt).run(allow_other=args.allow_other)
        return 0
    if args.cmd == "complete":
        return complete(args.outcome, args.reason)
    if args.cmd == "status":
        return status()
    STATE.mkdir(parents=True, exist_ok=True)
    if args.cmd == "clear-halt":
        for name in ("HALT", "STOP", "STOP_AFTER_ROUND", "deadline.json"):
            (STATE / name).unlink(missing_ok=True)
        return 0
    (STATE / {"stop": "STOP", "stop-after-round": "STOP_AFTER_ROUND"}[args.cmd]).touch()
    return 0


if __name__ == "__main__":
    sys.exit(main())
