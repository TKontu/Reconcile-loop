"""Load and validate supervisor settings; derive the autonomy that committed policy grants."""

import copy
import subprocess
import tomllib
from pathlib import Path

COMMITTED = ".agent/supervisor.toml"
LOCAL = ".agent/supervisor.local.toml"
ROLES = ("planner", "executor", "reviewer", "reconciler")
LOCAL_SECTIONS = {"runner", "budgets"}

# Every key and its default; the default's type is the required type.
DEFAULTS = {
    "supervisor": {
        "autonomy": 1,
        "remote": "origin",
        "worktree_root": "",
        "max_parallel": 1,
        "max_assignments": 3,
        "poll_seconds": 60,
        "launch_grace_seconds": 120,
    },
    "budgets": {
        "round_usd": 20.0,
        "sessions_per_round": 12,
        "max_rounds_per_run": 1,
        "ci_timeout_minutes": 60,
    },
    "stop": {"stall_rounds": 2, "max_repairs": 2},
    "notify": {"command": []},
    "policy": {
        "merge": {
            "auto_merge": False,
            "method": "squash",
            "required_checks": [],
            "protected_paths": [],
            "max_changed_lines": 400,
            "publish_reviews": True,
        },
        "reconcile": {
            "auto_reconcile": False,
            "allow_reconcile_merge": False,
            "record_paths": [],
        },
    },
    "runner": {"default": "claude", "env_drop": [], "commands": {}, "roles": {}},
}
COMMAND = {"argv": [], "output": {}}
ROLE = {
    "runner": "",
    "model": "",
    "budget_usd": 5.0,
    "timeout_minutes": 30,
    "permission_mode": "",
    "allowed_tools": [],
    "disallowed_tools": [],
}
POSITIVE = {
    "supervisor.autonomy",
    "supervisor.max_parallel",
    "supervisor.max_assignments",
    "supervisor.poll_seconds",
    "budgets.sessions_per_round",
    "budgets.max_rounds_per_run",
    "budgets.ci_timeout_minutes",
    "stop.stall_rounds",
    "policy.merge.max_changed_lines",
    "timeout_minutes",
}
CHOICES = {"supervisor.autonomy": {1, 2, 3}, "policy.merge.method": {"squash", "merge", "rebase"}}


class ConfigError(ValueError):
    pass


def fail(message):
    raise ConfigError(message)


def check_value(name, value, default):
    leaf = name.rsplit(".", 1)[-1]
    if isinstance(default, bool) or isinstance(default, str):
        ok = type(value) is type(default)
    elif isinstance(default, float):
        ok = type(value) in (int, float)
    elif isinstance(default, int):
        ok = type(value) is int
    else:
        ok = isinstance(value, list) and all(isinstance(v, str) and v for v in value)
    if not ok:
        fail(f"{name} must be {type(default).__name__}" + (" of strings" if isinstance(default, list) else ""))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if (name in POSITIVE or leaf in POSITIVE) and value < 1:
            fail(f"{name} must be at least 1")
        if value < 0:
            fail(f"{name} must not be negative")
    if name in CHOICES and value not in CHOICES[name]:
        fail(f"{name} must be one of {sorted(CHOICES[name])}")
    return float(value) if isinstance(default, float) else value


def merge(name, value, defaults):
    if not isinstance(value, dict):
        fail(f"{name} must be a table")
    out = copy.deepcopy(defaults)
    for key, item in value.items():
        path = f"{name}.{key}" if name else key
        if key not in defaults:
            fail(f"Unknown setting {path}")
        if path == "runner.commands":
            out[key] = {n: merge(f"{path}.{n}", v, COMMAND) for n, v in check_table(path, item)}
            for n, command in out[key].items():
                if not command["argv"]:
                    fail(f"{path}.{n}.argv must not be empty")
                for field, target in command["output"].items():
                    if not isinstance(target, str) or not target:
                        fail(f"{path}.{n}.output.{field} must be a string")
        elif path == "runner.roles":
            for role, _ in check_table(path, item):
                if role not in ROLES:
                    fail(f"Unknown role {path}.{role}")
            out[key] = {role: merge(f"{path}.{role}", v, ROLE) for role, v in item.items()}
        elif path.endswith(".output"):
            out[key] = dict(check_table(path, item))
        elif isinstance(defaults[key], dict):
            out[key] = merge(path, item, defaults[key])
        else:
            out[key] = check_value(path, item, defaults[key])
    return out


def check_table(name, value):
    if not isinstance(value, dict):
        fail(f"{name} must be a table")
    return value.items()


def deep_update(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value


def parse(committed, local=None):
    """Validate committed TOML text, then apply a local override of runner/budget keys only."""
    try:
        data = tomllib.loads(committed)
        override = tomllib.loads(local) if local is not None else {}
    except tomllib.TOMLDecodeError as error:
        fail(f"Invalid TOML: {error}")
    extra = set(override) - LOCAL_SECTIONS
    if extra:
        fail(f"The local override may set only {sorted(LOCAL_SECTIONS)}, not {sorted(extra)}")
    deep_update(data, override)
    return merge("", data, DEFAULTS)


def effective_autonomy(settings, ceiling=None):
    """The configured level, refused unless committed policy grants it; a ceiling only lowers."""
    level = settings["supervisor"]["autonomy"]
    merge_policy = settings["policy"]["merge"]
    reconcile = settings["policy"]["reconcile"]
    missing = []
    if level >= 2:
        missing += [g for g in ("auto_merge",) if not merge_policy[g]]
        missing += [] if merge_policy["required_checks"] else ["required_checks"]
    if level >= 3:
        missing += [g for g in ("auto_reconcile", "allow_reconcile_merge") if not reconcile[g]]
    if missing:
        fail(f"Autonomy {level} needs committed grants: {', '.join(missing)}")
    return min(level, ceiling) if ceiling else level


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
    )


def load(repo, remote, branch):
    """Read policy from the committed default branch, never from the working tree."""
    repo = Path(repo).resolve()
    shown = git(repo, "show", f"refs/remotes/{remote}/{branch}:{COMMITTED}")
    if shown.returncode:
        fail(f"No committed {COMMITTED} on {remote}/{branch}: {shown.stderr.strip()}")
    local = repo / LOCAL
    local_text = None
    if local.exists():
        if git(repo, "check-ignore", "-q", LOCAL).returncode:
            fail(f"{LOCAL} must be ignored by Git")
        local_text = local.read_text()
    settings = parse(shown.stdout, local_text)
    supervisor = settings["supervisor"]
    root = Path(supervisor["worktree_root"] or f"../{repo.name}-worktrees")
    root = (repo / root).resolve() if not root.is_absolute() else root.resolve()
    if root == repo or root.is_relative_to(repo):
        fail(f"supervisor.worktree_root must be outside the repository: {root}")
    supervisor["worktree_root"] = str(root)
    return settings
