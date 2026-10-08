"""Assign tasks and manage worker loop processes.

Workers run in detached process groups. Graceful stop uses a ``.stop`` flag
at the next round boundary; forced stop signals the entire process group.
"""

from __future__ import annotations

import fcntl
import json
import os
import time
from typing import Dict, List, Optional

from pharos import codex
from pharos.execution import layout as L
from pharos.execution.scaffold import atomic_write, spawn_loop
from .services import is_alive as _alive, kill_group


def _read_pid(wl: L.WorkerLayout) -> Optional[int]:
    pf = wl.pid
    if not pf.exists():
        return None
    try:
        return int(pf.read_text().strip())
    except (ValueError, OSError):
        return None


def _read_status(wl: L.WorkerLayout) -> Dict:
    sp = wl.status
    if not sp.exists():
        return {}
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def do_assign(target: str, task: str) -> Dict:
    """Replace a worker's task after checking its assignment and report state."""
    project, worker = L.resolve_target(target)
    if not worker:
        raise SystemExit("assign needs a specific worker: <project>/<worker>")
    wl = L.WorkerLayout(L.worker_dir(project, worker))
    if not wl.dir.is_dir():
        raise SystemExit(f"no such worker: {project}/{worker}")
    if not task.strip():
        raise SystemExit("refusing to assign an empty task")
    st = _read_status(wl)
    if st.get("round", 0) and st.get("state") in {"running", "report_missing"}:
        raise SystemExit("worker must finish its round report before reassignment")
    if st.get("round", 0) and (not list(wl.worker_reports.glob("*.md")) or not st.get("latest_report")):
        raise SystemExit("worker report is missing; reassignment is blocked")
    atomic_write(wl.task, task if task.endswith("\n") else task + "\n")
    return {"worker": f"{project}/{worker}", "task_file": str(wl.task)}


def _start_one(wl: L.WorkerLayout) -> str:
    """Returns 'started' / 'already-running' / 'locked'. Idempotent via an flock
    on .pid.lock; clears a stale .stop before spawning."""
    wl.dir.mkdir(parents=True, exist_ok=True)
    wl.logs.mkdir(exist_ok=True)
    lock = open(wl.lock, "w")
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return "locked"
        if _alive(_read_pid(wl)):
            return "already-running"
        wl.stop.unlink(missing_ok=True)  # clear a stale stop flag
        pid = spawn_loop(wl.dir)
        atomic_write(wl.pid, str(pid))
        return "started"
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def do_start(target: str, stagger: float = 0.2) -> List[Dict]:
    dirs = L.target_worker_dirs(target)
    if not dirs:
        raise SystemExit(f"no workers for target {target!r}")
    out = []
    for i, wdir in enumerate(dirs):
        if i and stagger:
            time.sleep(stagger)
        out.append({"worker": wdir.name, "result": _start_one(L.WorkerLayout(wdir))})
    # Record elapsed-run time for usage reports.
    project, _ = L.resolve_target(target)
    meta_path = L.project_dir(project) / "project.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["last_started_at"] = int(time.time())
        atomic_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError):
        pass  # Timestamp bookkeeping must not prevent worker startup.
    return out


SILENT_S = int(os.environ.get("PHAROS_SILENT_SECONDS", "1800"))


def worker_status(wl: L.WorkerLayout) -> Dict:
    pid = _read_pid(wl)
    alive = _alive(pid)
    st = _read_status(wl)
    state = st.get("state", "—")
    now = time.time()
    last = st.get("last_round_at") or st.get("round_started_at") or st.get("updated_at")
    age = (now - last) if isinstance(last, (int, float)) else None

    active_at = codex.last_activity(wl.codex_home)
    silent = (now - active_at) if active_at else None
    if alive:
        # Distinguish long rounds from sessions that have stopped writing activity.
        rs = st.get("round_started_at")
        hard = int(os.environ.get("PHAROS_ROUND_HARD_TIMEOUT", "14400"))
        if state == "running" and isinstance(rs, (int, float)) and (now - rs) > hard * 1.5:
            label = "stuck?"
        elif state == "running" and silent is not None and silent > SILENT_S:
            label = "silent?"
        elif state == "idle" and st.get("consec_fail"):
            label = f"failing x{st['consec_fail']}"
        else:
            label = "working"
    else:
        label = state if state in ("stopped", "deadline", "max_rounds", "error",
                                   "terminated", "created") else "dead"
    return {
        "worker": wl.name, "pid": pid, "alive": alive, "state": state,
        "round": st.get("round", 0), "age_s": round(age, 1) if age is not None else None,
        "last_fact_id": st.get("last_fact_id"), "label": label,
        "active_at": active_at, "silent_s": round(silent, 1) if silent is not None else None,
    }


def do_status(target: str) -> List[Dict]:
    dirs = L.target_worker_dirs(target)
    if not dirs:
        raise SystemExit(f"no workers for target {target!r}")
    return [worker_status(L.WorkerLayout(d)) for d in dirs]


def do_list() -> List[Dict]:
    """One row per project: roster + how many workers are live + model."""
    out: List[Dict] = []
    for project in L.list_projects():
        meta = {}
        mp = L.project_dir(project) / "project.json"
        if mp.exists():
            try:
                meta = json.loads(mp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
        workers = L.list_workers(project)
        live = sum(1 for w in workers
                   if _alive(_read_pid(L.WorkerLayout(L.worker_dir(project, w)))))
        out.append({"project": project, "workers": len(workers), "live": live,
                    "model": meta.get("model", "—")})
    return out


def _stop_one(wl: L.WorkerLayout, force: bool) -> str:
    pid = _read_pid(wl)
    if not force:
        if not _alive(pid):
            return "not-running"
        wl.stop.touch()      # graceful: loop exits at round boundary
        return "stopping (graceful)"
    # force: kill the loop's process group (loop + its codex child)
    killed = kill_group(pid)
    wl.pid.unlink(missing_ok=True)
    return "killed" if killed else "not-running"


def do_stop(target: str, force: bool = False) -> List[Dict]:
    dirs = L.target_worker_dirs(target)
    if not dirs:
        raise SystemExit(f"no workers for target {target!r}")
    return [{"worker": d.name, "result": _stop_one(L.WorkerLayout(d), force)}
            for d in dirs]
