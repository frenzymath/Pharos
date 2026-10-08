"""Project services and main-agent sessions.

Services run in detached process groups with PID files under ``runtime/run/``.
Main agents run in named tmux sessions. Recovery enumerates project metadata.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from pharos import codex
from pharos.execution import layout as L

DEFAULT_VERIFY_TIMEOUT = "90000"
_CODEX_TIMEOUT_SECONDS = "86400"


def _runtime() -> Path:
    return Path(os.environ.get("PHAROS_RUNTIME") or (L.repo_root() / "runtime"))


def _run_dir() -> Path:
    d = _runtime() / "run"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_dir() -> Path:
    d = _runtime() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pidfile(name: str) -> Path:
    return _run_dir() / f"{name}.pid"


def _read_pid(name: str) -> Optional[int]:
    try:
        return int(_pidfile(name).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def is_alive(pid: Optional[int]) -> bool:
    """Check process liveness, excluding zombies through ``/proc`` state."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True      # exists, owned by someone else
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        return stat.rsplit(")", 1)[1].split()[0] != "Z"   # field after "(comm)"
    except (OSError, IndexError):
        return True


_alive = is_alive


def kill_group(pid: Optional[int], grace: float = 5.0) -> bool:
    """Send SIGTERM, then SIGKILL after ``grace`` seconds if still alive.

    Detached agents have matching process and group IDs. Signal the group
    directly to reach child processes even if the group leader has exited.
    Return whether a signal was sent.
    """
    if not pid:
        return False
    signalled = False
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 0.0)):
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            return signalled
        except PermissionError:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                return signalled
        signalled = True
        end = time.time() + wait
        while wait and time.time() < end and _alive(pid):
            time.sleep(0.1)
        if not _alive(pid):
            return True
    return signalled


def _spawn(name: str, cmd: List[str], env: Dict[str, str], cwd: Optional[Path] = None,
           log_path: Optional[Path] = None) -> Dict:
    """Start a detached service, record its PID, and check that it stays up."""
    pid = _read_pid(name)
    if _alive(pid):
        return {"service": name, "result": f"already up (pid {pid})"}
    log_path = log_path or _log_dir() / f"{name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            cmd, stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True, env=env, cwd=str(cwd) if cwd else None,
        )
    _pidfile(name).write_text(str(proc.pid), encoding="utf-8")
    time.sleep(1)
    if proc.poll() is not None:
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]
        return {"service": name, "result": f"FAILED to start (see {log_path})",
                "log_tail": tail}
    return {"service": name, "result": f"up (pid {proc.pid}; log: {log_path})"}


def _stop(name: str) -> Dict:
    """Graceful SIGTERM to the whole process group, then SIGKILL after 2s."""
    pid = _read_pid(name)
    killed = kill_group(pid, grace=2.0)
    _pidfile(name).unlink(missing_ok=True)
    return {"service": name,
            "result": f"stopped (was pid {pid})" if killed else "not running"}


def verify_service_name(project: str) -> str:
    return f"verify-{project}"


def verify_port(project: str) -> int:
    """The project's allocated port, from its project.json."""
    from .cli import _project_meta        # local import: cli imports this module
    port = _project_meta(project).get("verify_port")
    if not isinstance(port, int):
        raise SystemExit(
            f"project {project!r} has no verify_port in project.json "
            "(add a free port to project.json)"
        )
    return port


def verify_health(project: str) -> Dict:
    """Classify the verify service as ours, foreign, stale, or down.

    Match the PID reported by ``/health`` to the PID file to distinguish another
    deployment listening on the same port.
    """
    port = verify_port(project)
    ours = _read_pid(verify_service_name(project))
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        state = "stale" if ours else "down"
        return {"state": state, "port": port, "pid": ours}
    answered = body.get("pid") if isinstance(body, dict) else None
    state = "ours" if (ours and answered == ours) else "foreign"
    return {"state": state, "port": port, "pid": ours, "answered_by": answered}


def verify_up(project: str) -> Dict:
    """Start this project's verify service: its own port, its own run logs, and
    its own codex session store, all inside the project directory."""
    from pharos.execution.scaffold import ensure_verifier_home, port_is_free

    pdir = L.project_dir(project)
    port = verify_port(project)
    name = verify_service_name(project)
    # Report port collisions before spawning the service.
    if not _alive(_read_pid(name)) and not port_is_free(port):
        return {"service": name,
                "result": (f"FAILED: port {port} is held by another process on this host "
                           f"(a foreign deployment?). Move this project to a free port — "
                           f"`pharos verify port {project} <N>` — then `pharos verify up` again; "
                           f"and give this deployment its own VERIFY_PORT base in config/pharos.env")}
    # Refresh contract and skill links at service startup.
    ensure_verifier_home(project)

    env = os.environ.copy()
    env.update({
        "VERIFY_AGENT_HOME": str(L.verifier_dir(project)),        # the codex -C dir
        "CODEX_HOME": str(L.verifier_codex_home(project)),        # its sessions
        "VERIFIER_RESULTS_DIR": str(L.verifier_runs_dir(project)),
        "VERIFY_PORT": str(port),
        "VERIFY_HOST": env.get("VERIFY_HOST", "127.0.0.1"),
        "CODEX_TIMEOUT_SECONDS": env.get("CODEX_TIMEOUT_SECONDS", _CODEX_TIMEOUT_SECONDS),
        "PHAROS_VERIFY_TIMEOUT": env.get("PHAROS_VERIFY_TIMEOUT", DEFAULT_VERIFY_TIMEOUT),
    })
    row = _spawn(verify_service_name(project),
                 [sys.executable, "-m", "pharos.verify"], env, cwd=pdir,
                 log_path=L.verifier_dir(project) / "service.log")
    row["port"] = port
    return row


def verify_down(project: str) -> Dict:
    return _stop(verify_service_name(project))


def verify_set_port(project: str, port: int) -> Dict:
    """``pharos verify port``: move the project's verify service to ``port``.
    Refused while the service is up (bring it down first); the new port must be
    unclaimed by every sibling project and free on the host. Workers pick the
    new URL up at their next loop start (their configs are regenerated then)."""
    from pharos.execution.scaffold import set_verify_port

    name = verify_service_name(project)
    pid = _read_pid(name)
    if _alive(pid):
        raise SystemExit(f"{name} is up (pid {pid}); `pharos verify down {project}` first")
    return set_verify_port(project, port)


def verify_status(projects: List[str]) -> List[Dict]:
    out = []
    for p in projects:
        try:
            row = verify_health(p)
        except SystemExit as exc:
            out.append({"project": p, "state": "unknown", "detail": str(exc)})
            continue
        row["project"] = p
        out.append(row)
    return out


def index_service_name(project: str) -> str:
    return f"index-{project}"


def index_port(project: str) -> Optional[int]:
    """The project's index port from its project.json, or ``None`` until the
    first ``pharos index up`` allocates one."""
    from .cli import _project_meta        # local import: cli imports this module
    port = _project_meta(project).get("index_port")
    return port if isinstance(port, int) else None


def _allocate_index_port(project: str) -> int:
    """Pick a free loopback port for this project's index service and record it
    in project.json: verify_port + 1000 if free, else the next free one above,
    never one a sibling project already uses (verify or index)."""
    from pharos.execution.scaffold import atomic_write, port_is_free

    taken = set()
    for p in L.list_projects():
        try:
            meta = json.loads((L.project_dir(p) / "project.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for key in ("verify_port", "index_port"):
            if isinstance(meta.get(key), int):
                taken.add(meta[key])
    port = verify_port(project) + 1000
    while port in taken or not port_is_free(port):
        port += 1
        if port > 65000:
            raise SystemExit("no free port for the index service")
    meta_path = L.project_dir(project) / "project.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["index_port"] = port
    atomic_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
    return port


def index_health(project: str) -> Dict:
    """``{"state": ours|foreign|stale|down|unconfigured, "port": int|None}`` —
    same classification as ``verify_health`` (the pid in ``/health`` must be
    ours)."""
    port = index_port(project)
    ours = _read_pid(index_service_name(project))
    if port is None:
        return {"state": "unconfigured", "port": None, "pid": ours}
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return {"state": "stale" if ours else "down", "port": port, "pid": ours}
    answered = body.get("pid") if isinstance(body, dict) else None
    return {"state": "ours" if (ours and answered == ours) else "foreign",
            "port": port, "pid": ours, "answered_by": answered}


def index_up(project: str) -> Dict:
    """Start the shared project index, allocating a port on first use.

    Gateways read the service configuration on each search.
    """
    from pharos.execution.scaffold import port_is_free

    pdir = L.project_dir(project)
    name = index_service_name(project)
    port = index_port(project) or _allocate_index_port(project)
    if not _alive(_read_pid(name)) and not port_is_free(port):
        return {"service": name,
                "result": (f"FAILED: port {port} is held by another process on this host; "
                           f"change `index_port` in {pdir / 'project.json'} to a free port and "
                           f"`pharos index up` again")}
    env = os.environ.copy()
    env.update({
        "PHAROS_PROJECT_DIR": str(pdir),
        "PHAROS_INDEX_PORT": str(port),
        "PHAROS_INDEX_HOST": env.get("PHAROS_INDEX_HOST", "127.0.0.1"),
    })
    row = _spawn(name, [sys.executable, "-m", "pharos.index"], env, cwd=pdir)
    row["port"] = port
    return row


def index_down(project: str) -> Dict:
    return _stop(index_service_name(project))


def index_status(projects: List[str]) -> List[Dict]:
    out = []
    for p in projects:
        try:
            row = index_health(p)
        except SystemExit as exc:
            out.append({"project": p, "state": "unknown", "detail": str(exc)})
            continue
        row["project"] = p
        out.append(row)
    return out


def monitor_service_name(project: str) -> str:
    return f"monitor-{project}"


def monitor_up(project: str) -> Dict:
    """Start the project's liveness/load sampler, detached. It appends one line
    per interval to ``<project>/monitor.jsonl`` and only observes."""
    if not (L.project_dir(project) / "project.json").is_file():
        raise SystemExit(f"unknown project: {project}")
    env = L.child_env()
    env["PHAROS_AGENTS_ROOT"] = str(L.agents_root())
    return _spawn(monitor_service_name(project),
                  [sys.executable, "-m", "pharos.orchestration.monitor", project], env,
                  log_path=L.project_dir(project) / "monitor.log")


def monitor_down(project: str) -> Dict:
    return _stop(monitor_service_name(project))


def monitor_status(projects: List[str]) -> List[Dict]:
    return [{"project": p, "state":
             "up" if _alive(_read_pid(monitor_service_name(p))) else "down"}
            for p in projects]


# The project contract supplies the main agent's operating instructions.
_MAIN_PROMPT = ("You are the main agent for Pharos project {project} "
                "(this directory). Read AGENTS.md and begin.")


def _default_tag(project: str) -> str:
    """A 3–4 char fallback abbreviation, when the operator gave none."""
    letters = [c for c in project.lower() if c.isalnum()]
    return "".join(letters[:4]) or "proj"


def main_tag(project: str) -> str:
    """This experiment's short tag — recorded in project.json by the first
    ``pharos main start``, so `status` and the attach hint resolve the same
    session name later."""
    from .cli import _project_meta
    try:
        tag = _project_meta(project).get("tag")
    except SystemExit:
        tag = None
    return tag if isinstance(tag, str) and tag else _default_tag(project)


def set_main_tag(project: str, tag: str) -> None:
    """Persist the tag so every later command finds the same tmux session."""
    meta_path = L.project_dir(project) / "project.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["tag"] = tag
    tmp = meta_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(meta_path)


def main_session_name(project: str) -> str:
    """The experiment's tmux session: ``pharos-v3-<tag>``."""
    return f"pharos-v3-{main_tag(project)}"


def main_start(project: str, tag: Optional[str] = None) -> Dict:
    """Start a detached tmux session with the project's directory and Codex home."""
    pdir = L.project_dir(project)
    if not (pdir / "project.json").is_file():
        raise SystemExit(f"unknown project: {project} (pharos new {project} first)")
    if tag:
        if not (2 <= len(tag) <= 8 and tag.isalnum() and tag.islower()):
            raise SystemExit(
                f"tag {tag!r} must be 2–8 lowercase alphanumerics — a short "
                f"abbreviation of the project (proof-demo -> demo)"
            )
        set_main_tag(project, tag)
    session = main_session_name(project)
    if subprocess.run(["tmux", "has-session", "-t", session],
                      capture_output=True).returncode == 0:
        return {"session": session, "result": "already running",
                "attach": f"tmux attach -t {session}"}
    codex.provision_codex_home(L.main_codex_home(project))
    try:
        project_model = json.loads((pdir / "project.json").read_text(encoding="utf-8"))["model"]
    except (OSError, json.JSONDecodeError, KeyError):
        project_model = codex.model()
    env = os.environ.copy()
    env["CODEX_HOME"] = str(L.main_codex_home(project))
    completed = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session, "-c", str(pdir),
         # A long-lived tmux server keeps the environment of the first project
         # that created it. Override per-session values in the pane command so
         # later projects cannot inherit that project's model or session store.
         "env", f"CODEX_HOME={L.main_codex_home(project)}",
         f"PHAROS_CODEX_MODEL={project_model}",
         codex.resolve_bin(), "--dangerously-bypass-approvals-and-sandbox",
         _MAIN_PROMPT.format(project=project)],
        env=env, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(f"tmux failed to start {session}: {completed.stderr.strip()}")
    return {"session": session, "result": f"started in {pdir}",
            "attach": f"tmux attach -t {session}"}


def main_status(projects: List[str]) -> List[Dict]:
    """Which projects have a live main-agent tmux session."""
    listed = subprocess.run(["tmux", "ls", "-F", "#{session_name}"],
                            capture_output=True, text=True)
    live = set(listed.stdout.split()) if listed.returncode == 0 else set()
    return [{"project": p, "session": main_session_name(p),
             "running": main_session_name(p) in live,
             "active_at": codex.last_activity(L.main_codex_home(p))} for p in projects]
