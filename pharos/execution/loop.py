"""Run successive worker sessions, resuming from persisted project memory.

Launched detached by ``pharos start`` (``python -m pharos.execution <worker_dir>``).
Each round runs one ``codex exec`` session. The loop stops at a round boundary
on a ``.stop`` flag, the project deadline, or the configured round limit.
Configuration is read at call time; ``pharos.codex`` resolves the command.

Environment:
  PHAROS_CODEX_BIN            override the codex command (default: `codex` on PATH)
  PHAROS_WORKER_MODEL         worker model (default "gpt-6-astra")
  PHAROS_ROUND_BEAT           seconds to sleep between rounds (default 5)
  PHAROS_ROUND_HARD_TIMEOUT   per-round hard timeout, seconds (default 14400 = 4h)
  PHAROS_MAX_ROUNDS           round backstop, 0 = unlimited (default 0)
  PHAROS_FAIL_BACKOFF_CAP     longest pause after consecutive failed rounds, seconds (default 600)
"""

from __future__ import annotations

import json
import os
import shutil
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from . import layout as L
from . import scaffold
from pharos import codex

_FACT_ID_RE = re.compile(r'"?fact_id"?\s*[:=]\s*"?([0-9a-f]{16})"?')


def kickoff(project: str, worker: str) -> str:
    # The worker's AGENTS.md supplies its operating instructions.
    return (
        f"You are worker '{worker}' on project '{project}'. This is a "
        f"continuation round: resume per your AGENTS.md contract. You MUST write the round report requested by the contract before ending this round."
    )


def _read_role(wl: L.WorkerLayout) -> dict:
    out = {"MODEL": os.environ.get("PHAROS_WORKER_MODEL") or codex.DEFAULT_MODEL,
           "REASONING_EFFORT": "xhigh", "ROLE": "xhigh", "PHAROS_AUTHOR": wl.name}
    rp = wl.role
    if rp.exists():
        for line in rp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def write_status(wl: L.WorkerLayout, **fields) -> None:
    """Atomic status write (so `pharos status` never reads a half-written file)."""
    path = wl.status
    cur = {}
    if path.exists():
        try:
            cur = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cur = {}
    cur.update(fields)
    cur["worker"] = wl.name
    cur["pid"] = os.getpid()
    cur["updated_at"] = time.time()
    # A signal handler can re-enter this function; give each writer its own file.
    fd, tmp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(cur, ensure_ascii=False, indent=2))
    os.replace(tmp, path)


def _deadline_passed(project_dir: Path) -> bool:
    f = project_dir / L.DEADLINE_FILE
    if not f.exists():
        return False
    try:
        return time.time() >= float(f.read_text().strip())
    except (ValueError, OSError):
        return False


def _parse_last_fact_id(log_path: Path) -> Optional[str]:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    ids = _FACT_ID_RE.findall(text)
    return ids[-1] if ids else None


class _Child:
    """Holds the running codex subprocess so the SIGTERM handler can kill it."""
    proc: "subprocess.Popen | None" = None


def _end_group(proc: subprocess.Popen, grace: float = 10.0) -> None:
    """End the round's process group with SIGTERM, then SIGKILL after ``grace``.

    The child starts a new session, so its PID is also its process group ID.
    """
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 2.0)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        end = time.time() + wait
        while time.time() < end:
            proc.poll()                      # reap the launcher once it is gone
            try:
                os.killpg(proc.pid, 0)       # raises when no member is left
            except ProcessLookupError:
                return
            time.sleep(0.2)


def run_round(wl: L.WorkerLayout, role: dict, prompt: str, log_path: Path,
              hard_timeout: int) -> int:
    """Exec one ``codex exec`` continuation session. Returns codex's rc, 124 on
    hard-timeout (the round's whole process group: SIGTERM → 10s → SIGKILL),
    or 127 if the codex binary is missing."""
    wdir = wl.dir
    codex_bin = codex.resolve_bin()
    if not (os.path.exists(codex_bin) or shutil.which(codex_bin)):
        log_path.write_text(f"[worker_loop] codex binary not found: {codex_bin}\n")
        return 127
    cmd = codex.exec_cmd(
        codex_bin, role["MODEL"], role["REASONING_EFFORT"],
        "-C", str(wdir),
        # Support source archives without a .git directory.
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        prompt,
    )
    with open(log_path, "w", encoding="utf-8") as logf:
        try:
            _Child.proc = subprocess.Popen(
                codex.low_priority(cmd), stdout=logf, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, cwd=str(wdir), start_new_session=True,
                env=codex.subprocess_env(codex_bin, codex_home=wl.codex_home),
            )
        except FileNotFoundError:
            logf.write(f"[worker_loop] codex binary not found: {cmd[0]}\n")
            return 127
        try:
            return _Child.proc.wait(timeout=hard_timeout if hard_timeout > 0 else None)
        except subprocess.TimeoutExpired:
            _end_group(_Child.proc)
            logf.write(f"\n[worker_loop] round hard-timeout after {hard_timeout}s\n")
            return 124
        finally:
            _Child.proc = None


def _cleanup_pid(wl: L.WorkerLayout) -> None:
    """Remove our own .pid if it still points at us (clean exit only)."""
    pf = wl.pid
    try:
        if pf.exists() and pf.read_text().strip() == str(os.getpid()):
            pf.unlink(missing_ok=True)
    except OSError:
        pass


def main(worker_dir: str) -> int:
    wdir = Path(worker_dir).resolve()
    if not wdir.is_dir():
        print(f"worker dir not found: {wdir}", file=sys.stderr)
        return 2
    wl = L.WorkerLayout(wdir)
    project_dir = wl.project_dir
    project = wl.project
    worker = wl.name
    role = _read_role(wl)

    # Refresh the interpreter path, shared configuration, and credentials on start.
    scaffold.write_codex_config(wl)
    codex.provision_codex_home(wl.codex_home)

    beat = float(os.environ.get("PHAROS_ROUND_BEAT", "5"))
    hard_timeout = int(os.environ.get("PHAROS_ROUND_HARD_TIMEOUT", "14400"))
    max_rounds = int(os.environ.get("PHAROS_MAX_ROUNDS", "0"))
    backoff_cap = float(os.environ.get("PHAROS_FAIL_BACKOFF_CAP", "600"))
    wl.logs.mkdir(parents=True, exist_ok=True)
    wl.worker_reports.mkdir(parents=True, exist_ok=True)
    prompt = kickoff(project, worker)

    def _on_term(_signum, _frame):
        if _Child.proc is not None:
            # shorter than kill_group's 5 s grace on this loop, so the SIGKILL
            # to the round's group is sent before the loop itself can be killed
            _end_group(_Child.proc, grace=3.0)
        write_status(wl, state="terminated")
        _cleanup_pid(wl)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_term)

    write_status(wl, state="running", round=0, started_at=time.time())
    # Resume numbering after the highest existing round log: a restarted loop
    # must never overwrite a previous generation's transcripts.
    rnd = max((int(p.stem[6:]) for p in wl.logs.glob("round_*.log")
               if p.stem[6:].isdigit()), default=0) if wl.logs.exists() else 0
    consec_fail = 0
    try:
        while True:
            if wl.stop.exists():
                wl.stop.unlink(missing_ok=True)
                write_status(wl, state="stopped")
                break
            if _deadline_passed(project_dir):
                write_status(wl, state="deadline")
                break
            if max_rounds and rnd >= max_rounds:
                write_status(wl, state="max_rounds")
                break

            rnd += 1
            log_path = wl.logs / f"round_{rnd}.log"
            round_started = time.time()
            write_status(wl, state="running", round=rnd, round_started_at=round_started)
            rc = run_round(wl, role, prompt, log_path, hard_timeout)
            consec_fail = consec_fail + 1 if rc not in (0, 124) else 0
            write_status(
                wl, state="idle", round=rnd, last_round_at=time.time(),
                last_rc=rc, last_fact_id=_parse_last_fact_id(log_path),
                consec_fail=consec_fail, error=None,
            )

            if rc == 127:                    # codex missing — do not spin
                write_status(wl, state="error", error="codex binary not found")
                return 127
            # Retry failed rounds with capped exponential backoff.
            if consec_fail:
                time.sleep(min(beat * 2 ** consec_fail, backoff_cap))
                continue
            reports = sorted(wl.worker_reports.glob("*.md"), key=lambda p: p.stat().st_mtime)
            if not reports or reports[-1].stat().st_mtime < round_started:
                write_status(wl, state="report_missing", round=rnd, last_rc=rc)
                time.sleep(beat if beat > 0 else 1)
                continue
            write_status(wl, latest_report=str(reports[-1]))
            if beat > 0:
                time.sleep(beat)
    finally:
        _cleanup_pid(wl)
    return 0
