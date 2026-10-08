"""Shared Codex launcher and the ``codex`` console command.

Resolve the binary, model, reasoning effort, and subprocess environment at
call time. ``PHAROS_CODEX_BIN``, ``PHAROS_CODEX_MODEL``, and
``PHAROS_CODEX_EFFORT`` set deployment defaults; callers can supply service
overrides through ``model()`` and ``effort()``.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MODEL = "gpt-6-astra"
DEFAULT_EFFORT = "max"

# Per-agent homes share configuration and credentials through symlinks.
_SHARED_HOME_FILES = ("config.toml", "auth.json")


def shared_codex_home() -> Path:
    """Shared Codex configuration written by ``setup-codex.sh``.

    ``CODEX_HOME`` is a per-agent session store. Resolve the shared location
    independently so agent homes link directly to it.
    """
    override = os.environ.get("PHAROS_CODEX_SHARED_HOME")
    if override:
        return Path(override)
    runtime = os.environ.get("PHAROS_RUNTIME") or str(_REPO_ROOT / "runtime")
    return Path(runtime) / "codex-home"


def provision_codex_home(home: Path) -> Path:
    """Create a session store with links to shared configuration and credentials.

    Replace stale links and skip sources that have not been provisioned yet.
    Loop and service startup call this again after setup.
    """
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    shared = shared_codex_home()
    if home.resolve() == shared.resolve():
        return home  # Avoid self-referential links.
    for name in _SHARED_HOME_FILES:
        target = shared / name
        link = home / name
        if not target.exists():
            continue
        if link.is_symlink():
            if link.resolve() == target.resolve():
                continue
            link.unlink()
        elif link.exists():
            link.unlink()
        link.symlink_to(target)
    return home


def resolve_bin() -> str:
    """Resolve Codex from an override, PATH, or the interpreter's directory.

    Return ``"codex"`` if none is found, leaving subprocess launch to report
    the missing executable.
    """
    override = os.environ.get("PHAROS_CODEX_BIN")
    if override:
        # Resolve bare names so subprocess_env can add the Node shebang's directory.
        if os.path.isabs(override):
            return override
        return shutil.which(override) or override
    which = shutil.which("codex")
    if which:
        return which
    sibling = Path(sys.executable).parent / "codex"
    if sibling.is_file() and os.access(sibling, os.X_OK):
        return str(sibling)
    return "codex"


def npm_prefix(codex_js: str) -> Optional[str]:
    """Return the npm prefix that owns a Codex JavaScript entry point."""
    path = Path(codex_js).expanduser()
    try:
        path = path.resolve()
    except OSError:
        return None
    package = path.parent.parent
    scope = package.parent
    node_modules = scope.parent
    lib = node_modules.parent
    if (path.parent.name == "bin" and package.name == "codex"
            and scope.name == "@openai" and node_modules.name == "node_modules"
            and lib.name == "lib"):
        return str(lib.parent)
    return None


def model(*override_env_names: str, default: str = DEFAULT_MODEL) -> str:
    """First nonempty service override, then ``PHAROS_CODEX_MODEL``, then default."""
    for name in override_env_names:
        val = os.environ.get(name)
        if val:
            return val
    return os.environ.get("PHAROS_CODEX_MODEL") or default


def effort(*override_env_names: str, default: str = DEFAULT_EFFORT) -> str:
    """First nonempty service override, then ``PHAROS_CODEX_EFFORT``, then default."""
    for name in override_env_names:
        val = os.environ.get(name)
        if val:
            return val
    return os.environ.get("PHAROS_CODEX_EFFORT") or default


def subprocess_env(codex_bin: str, *, codex_home: "Optional[Path | str]" = None) -> Dict[str, str]:
    """Copy the environment, pin the projects root, and select a session store.

    Add the binary's directory to PATH for its Node shebang. A bare command
    name must not add the current directory to PATH.
    """
    env = os.environ.copy()
    if codex_home is not None:
        env["CODEX_HOME"] = str(codex_home)
    if not env.get("PHAROS_AGENTS_ROOT"):
        from pharos.execution import layout as _L
        env["PHAROS_AGENTS_ROOT"] = str(_L.agents_root())
    if os.path.dirname(codex_bin):
        codex_dir = os.path.dirname(os.path.abspath(codex_bin))
        existing = env.get("PATH", "")
        parts = existing.split(os.pathsep) if existing else []
        if codex_dir not in parts:
            env["PATH"] = codex_dir + (os.pathsep + existing if existing else "")
    return env


def last_activity(codex_home: "Path | str") -> Optional[float]:
    """Latest session or history modification time, or ``None`` for a new home.

    Session files are searched within the newest nonempty ``sessions/Y/M/D``.
    """
    home = Path(codex_home)
    best: Optional[float] = None
    sessions = home / "sessions"
    if sessions.is_dir():
        for day in sorted(sessions.glob("*/*/*"), reverse=True):
            stamps = [f.stat().st_mtime for f in day.iterdir() if f.is_file()]
            if stamps:
                best = max(stamps)
                break
    history = home / "history.jsonl"
    if history.is_file():
        best = max(best or 0.0, history.stat().st_mtime)
    return best


def low_priority(cmd: List[str]) -> List[str]:
    """Add ``nice`` and ``ionice`` prefixes when available for background work."""
    prefix: List[str] = []
    if shutil.which("ionice"):
        prefix += ["ionice", "-c", "2", "-n", "7"]
    if shutil.which("nice"):
        prefix += ["nice", "-n", "10"]
    return prefix + list(cmd)


def exec_cmd(codex_bin: str, model: str, effort: str, *tail: str) -> List[str]:
    """Build ``codex exec`` arguments with a quoted effort value and caller tail."""
    return [
        codex_bin, "exec",
        "--model", model,
        "--config", f'model_reasoning_effort="{effort}"',
        *tail,
    ]

def _runtime_env() -> Dict[str, str]:
    """Read bootstrap paths for shells that have not sourced ``scripts/env.sh``."""
    out: Dict[str, str] = {}
    runtime = os.environ.get("PHAROS_RUNTIME") or str(_REPO_ROOT / "runtime")
    try:
        text = (Path(runtime) / "runtime.env").read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _human_codex_home(cwd: Path, shared: Path, env: Dict[str, str]) -> Optional[Path]:
    """Choose the session home for a human-launched Codex process.

    The repository root uses the shared home when inheriting a project home
    or the Codex default. Preserve explicit custom homes.
    """
    current = env.get("CODEX_HOME", "")
    if cwd == _REPO_ROOT:
        if not current or Path(current).expanduser() in {
            shared.expanduser(),
            (Path.home() / ".codex").expanduser(),
        }:
            return shared
        agents_root = Path(
            env.get("PHAROS_AGENTS_ROOT") or (shared.parent / "projects")
        ).expanduser()
        if agents_root in Path(current).expanduser().parents:
            return shared
    return None


def main(argv: Optional[List[str]] = None) -> int:
    """Run the bootstrap-provisioned Codex with a session home for this directory.

    Use a local ``.codex-home`` when present, unless ``CODEX_HOME`` selects an
    explicit custom home.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    runtime = _runtime_env()
    node = os.environ.get("PHAROS_NODE") or runtime.get("PHAROS_NODE", "")
    codex_js = os.environ.get("PHAROS_CODEX_JS") or runtime.get("PHAROS_CODEX_JS", "")
    if not (node and codex_js and os.path.isfile(codex_js) and os.access(node, os.X_OK)):
        print("codex is not provisioned (runtime/runtime.env missing or stale)", file=sys.stderr)
        print(f"Run: bash {_REPO_ROOT / 'scripts' / 'bootstrap.sh'}", file=sys.stderr)
        return 126
    env = os.environ.copy()
    if not env.get("NPM_CONFIG_PREFIX"):
        prefix = env.get("PHAROS_CODEX_NPM_PREFIX") or npm_prefix(codex_js)
        if prefix:
            env["NPM_CONFIG_PREFIX"] = prefix
    shared = str(shared_codex_home())
    cwd = Path.cwd()
    human_home = _human_codex_home(cwd, Path(shared), env)
    if human_home is not None:
        env["CODEX_HOME"] = str(human_home)
    if (cwd / ".codex-home").is_dir() and env.get("CODEX_HOME") in (None, "", shared):
        env["CODEX_HOME"] = str(cwd / ".codex-home")
    os.execve(node, [node, codex_js, *args], env)
