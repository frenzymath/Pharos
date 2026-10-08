"""Section writing, verification, and paper assembly.

Each section under ``paper/src/sections/`` has a writer and verifier. A writer
report of ``done`` starts verification; ``pass`` completes the section and
``fail`` starts another writing round. ``escalate`` and ``failed`` stop the
loop. Failed processes are retried with backoff without reading stale reports.

Writers and verifiers resume their own sessions. At
``PHAROS_PAPER_ATTENTION_ROUNDS`` (default 5), ``wait`` returns once to request
review while the section loop continues. Whole-paper verification runs in
``paper/verifier/`` through ``pharos paper verify --global``.
"""

from __future__ import annotations

import json
import itertools
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from pharos import codex
from pharos.execution import layout as L
from pharos.execution.scaffold import (atomic_write, ensure_paper_workspace,
                                      ensure_section_home)

from .services import is_alive, kill_group

REPORT, VERDICT, STATE = "REPORT.md", "VERDICT.md", ".state.json"

# Missing backslashes in \quad and \qquad can produce valid but unintended TeX.
_QUAD_SLIP = re.compile(r"(?:^|[^\\A-Za-z])q?quad(?:[^A-Za-z]|$)")
_TEX_COMMENT = re.compile(r"(?<!\\)%")


def lint_section(path: Path) -> List[str]:
    """The lines of ``path`` that carry a ``quad``/``qquad`` without its
    backslash, TeX comments ignored: ``"<line no>: <line>"`` each."""
    hits = []
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if _QUAD_SLIP.search(_TEX_COMMENT.split(line, 1)[0]):
            hits.append(f"{no}: {line.strip()}")
    return hits


def _attention_round() -> int:
    return int(os.environ.get("PHAROS_PAPER_ATTENTION_ROUNDS", "5"))

PROMPT_WRITE = ("Read AGENTS.md and TASK.md. If verifier/VERDICT.md exists it is your own "
                "verifier's latest judgment of your draft — address it. Do this round's "
                "work and finish by writing REPORT.md.")
PROMPT_VERIFY = ("Read AGENTS.md; verify section.tex against TASK.md, the outline, and "
                 "the project's facts; write VERDICT.md.")
PROMPT_VERIFY_WHOLE = ("Read AGENTS.md; verify ../src/main.tex — every section together — "
                       "against ../OUTLINE.tex and the project's facts; write VERDICT.md.")


def _first_word(path: Path) -> Optional[str]:
    """``status: done`` -> ``done``; None when missing/empty."""
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return None
    return first.partition(":")[2].strip().lower() or None


def _read_pid(home: Path) -> Optional[int]:
    try:
        return int((home / L.PID_FILE).read_text().strip())
    except (OSError, ValueError):
        return None


def _state(home: Path) -> Dict:
    try:
        return json.loads((home / STATE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _set_state(home: Path, **kw) -> None:
    st = _state(home)
    st.update(kw, updated_at=time.time())
    atomic_write(home / STATE, json.dumps(st, indent=2))


def _launch_argv(home: Path) -> List[str]:
    bin_, model, effort = codex.resolve_bin(), codex.model(), codex.effort()
    tail = ["--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox", "-"]
    sessions = home / ".codex-home" / "sessions"
    if sessions.is_dir() and any(sessions.rglob("*.jsonl")):
        return [bin_, "exec", "resume", "--last", "--model", model,
                "--config", f'model_reasoning_effort="{effort}"', *tail]
    return codex.exec_cmd(bin_, model, effort, "-C", str(home), *tail)


def _run_session(home: Path, prompt: str, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as logf:
        return subprocess.run(
            _launch_argv(home), input=prompt, text=True, stdout=logf,
            stderr=subprocess.STDOUT, cwd=str(home),
            env=codex.subprocess_env(codex.resolve_bin(), codex_home=home / ".codex-home"),
        ).returncode


def _session(state_home: Path, home: Path, prompt: str, log_path: Path) -> None:
    """Retry failed sessions with backoff before consuming their report.

    Keep each attempt's output in ``<stem>.retry<n>.log``.
    """
    beat = float(os.environ.get("PHAROS_ROUND_BEAT", "5"))
    cap = float(os.environ.get("PHAROS_FAIL_BACKOFF_CAP", "600"))
    stem = log_path.with_suffix("")
    for attempt in itertools.count(1):
        rc = _run_session(home, prompt, log_path)
        if rc == 0:
            return
        if rc == 127:
            raise SystemExit("codex binary not found")
        _set_state(state_home, note=f"codex exited {rc} in {log_path.name}; retry {attempt}")
        time.sleep(min(beat * 2 ** attempt, cap))
        log_path = stem.with_name(f"{stem.name}.retry{attempt}.log")


def section_loop(project: str, name: str) -> int:
    home = ensure_section_home(project, name)
    vhome = L.section_verifier_dir(project, name)
    _set_state(home, attention_seen=False)      # a fresh run of the loop may raise attention again
    for rnd in itertools.count(1):
        _set_state(home, state="running", phase="writing", round=rnd,
                   note=(f"round {rnd} without a pass — review the outline and the task"
                         if rnd >= _attention_round() else None))
        _session(home, home, PROMPT_WRITE, home / L.LOGS_DIR / f"round_{rnd}_write.log")
        word = _first_word(home / REPORT)
        if word == "escalate":
            _set_state(home, state="escalate", phase=None)
            return 0
        if word != "done":
            _set_state(home, state="failed", phase=None, note=f"writer reported {word}")
            return 1
        _set_state(home, phase="verifying")
        _session(home, vhome, PROMPT_VERIFY, vhome / L.LOGS_DIR / f"round_{rnd}.log")
        verdict = _first_word(vhome / VERDICT)
        _set_state(home, verdict=verdict)
        if verdict == "pass":
            _set_state(home, state="done", phase=None)
            return 0


def assign(project: str, section: str, task: str) -> Dict:
    if not task.strip():
        raise SystemExit("refusing to assign an empty task")
    home = ensure_section_home(project, section)
    atomic_write(home / L.TASK_FILE, task if task.endswith("\n") else task + "\n")
    return {"section": section, "task_file": str(home / L.TASK_FILE)}


def _sections(project: str) -> List[str]:
    root = L.sections_dir(project)
    return sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []


def _start_one(project: str, name: str) -> str:
    home = ensure_section_home(project, name)
    if not (home / L.TASK_FILE).is_file():
        return "unassigned"
    if is_alive(_read_pid(home)):
        return "already-running"
    (home / L.LOGS_DIR).mkdir(exist_ok=True)
    env = L.child_env()
    env["PHAROS_AGENTS_ROOT"] = str(L.agents_root())
    with open(home / L.LOGS_DIR / "loop.log", "a", encoding="utf-8") as logf:
        proc = subprocess.Popen([sys.executable, "-m", "pharos.orchestration.paper",
                                 project, name], stdout=logf, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True,
                                cwd=str(home), env=env)
    atomic_write(home / L.PID_FILE, str(proc.pid))
    return "started"


def _pending(home: Path) -> bool:
    """A TASK.md newer than the last loop state — work the loop has not seen."""
    task = home / L.TASK_FILE
    return task.is_file() and task.stat().st_mtime > _state(home).get("updated_at", 0)


def start(project: str, section: Optional[str] = None, all_: bool = False) -> List[Dict]:
    if all_:
        return [{"section": n, "result": _start_one(project, n)} for n in _sections(project)
                if _pending(L.section_dir(project, n))]
    if not section:
        raise SystemExit("paper start needs a section, or --all")
    return [{"section": section, "result": _start_one(project, section)}]


def status(project: str) -> List[Dict]:
    out = []
    for name in _sections(project):
        home = L.section_dir(project, name)
        st = _state(home)
        if is_alive(_read_pid(home)):
            state = f"running:{st.get('phase') or '?'}"
        elif not (home / L.TASK_FILE).is_file():
            state = "unassigned"
        elif _pending(home):
            state = "assigned"
        else:
            state = st.get("state", "assigned")
        out.append({"name": name, "state": state, "round": st.get("round", 0),
                    "verdict": st.get("verdict"), "note": st.get("note"),
                    "age_s": round(time.time() - st.get("updated_at", time.time()), 1)})
    return out


def wait(project: str, sections: List[str], timeout: int) -> int:
    """Block until a section's loop ends — the first of the running ones, or
    every one named — or until a running section reaches the attention round
    without a pass (reported once per run of its loop; the loop keeps going)."""
    any_one = not sections
    pending = set(sections or [n for n in _sections(project)
                               if is_alive(_read_pid(L.section_dir(project, n)))])
    deadline = time.time() + timeout if timeout else None
    while pending:
        before = len(pending)
        for name in list(pending):
            home = L.section_dir(project, name)
            st = _state(home)
            if not is_alive(_read_pid(home)):
                pending.discard(name)
                print(f"{name}: {st.get('state', '?')}"
                      + (f" (verdict {st['verdict']})" if st.get("verdict") else "")
                      + (f" — {st['note']}" if st.get("note") else ""))
            elif st.get("round", 0) >= _attention_round() and not st.get("attention_seen"):
                _set_state(home, attention_seen=True)
                pending.discard(name)
                print(f"{name}: attention — round {st['round']} without a pass; "
                      f"still running — review the outline and the task")
        if any_one and len(pending) < before:
            return 0
        if pending and deadline and time.time() >= deadline:
            return 124
        if pending:
            time.sleep(3)
    return 0


def stop(project: str, section: str) -> Dict:
    home = L.section_dir(project, section)
    killed = kill_group(_read_pid(home))
    (home / L.PID_FILE).unlink(missing_ok=True)
    if killed:
        _set_state(home, state="stopped", phase=None)
    return {"section": section, "result": "stopped" if killed else "not-running"}


def verify(project: str, section: Optional[str] = None, whole: bool = False) -> int:
    """One verifier round, foreground: a section's own verifier, or the
    whole-paper one (``--global``)."""
    if whole or not section:
        ensure_paper_workspace(project)
        home, prompt = L.paper_verifier_dir(project), PROMPT_VERIFY_WHOLE
    else:
        ensure_section_home(project, section)
        home, prompt = L.section_verifier_dir(project, section), PROMPT_VERIFY
    _run_session(home, prompt, home / L.LOGS_DIR / f"{time.strftime('%Y%m%dT%H%M%S')}.log")
    word = _first_word(home / VERDICT)
    print(f"verdict: {word or '(none)'}")
    return {"pass": 0, "fail": 1}.get(word, 2)


def build(project: str, template: Optional[Path] = None) -> Path:
    """Assemble sorted sections into the project template and compile a PDF.

    Return ``main.tex`` when no TeX engine is available. Emit nonfatal lint
    warnings for ``quad`` and ``qquad`` without backslashes.
    """
    ensure_paper_workspace(project)
    tpl = template or (L.paper_src_dir(project) / "template.tex")
    if not tpl.is_file():
        raise SystemExit(f"paper template missing: {tpl}")
    names = [n for n in _sections(project)
             if (L.section_dir(project, n) / "section.tex").is_file()]
    for n in names:
        for hit in lint_section(L.section_dir(project, n) / "section.tex"):
            print(f"lint: sections/{n}/section.tex:{hit}   <- a \\quad or \\qquad without its backslash?")
    inputs = "\n".join(f"\\input{{sections/{n}/section.tex}}" for n in names)
    src = L.paper_src_dir(project)
    main_tex = src / "main.tex"
    # Preserve template comments; only the %%SECTIONS%% marker is expanded there.
    lines = [ln if ln.lstrip().startswith("%") and not ln.lstrip().startswith("%%SECTIONS%%")
             else ln.replace("%%SECTIONS%%", inputs).replace("%%TITLE%%", project)
             for ln in tpl.read_text(encoding="utf-8").splitlines(keepends=True)]
    atomic_write(main_tex, "".join(lines))

    engine = tex_engine()
    if not engine:
        print(f"assembled only (no TeX engine on PATH): {main_tex}")
        return main_tex
    err = tex_compile(engine, src, "main.tex")
    if err:
        raise SystemExit(f"TeX compile failed:\n{err}")
    out = L.paper_dir(project) / f"{L.stamped_name(project)}.pdf"
    shutil.copy(src / "main.pdf", out)
    print(f"built {out}")
    return out


def dispatch(project: str, args) -> int:
    a = args.action
    if a == "assign":
        from .cli import _task_from_args
        r = assign(project, args.section, _task_from_args(args))
        print(f"assigned {r['section']} -> {r['task_file']}")
    elif a == "start":
        for r in start(project, args.section, args.all):
            print(f"{r['section']}: {r['result']}")
    elif a == "status":
        rows = status(project)
        w = max([16] + [len(r["name"]) + 2 for r in rows])
        for r in rows:
            print(f"{r['name']:<{w}}{r['state']:<18}round={r['round']:<3}"
                  f"verdict={r['verdict'] or '—':<6}age={r['age_s']}s"
                  + (f"  {r['note']}" if r["note"] else ""))
    elif a == "wait":
        return wait(project, args.sections, args.timeout)
    elif a == "stop":
        r = stop(project, args.section)
        print(f"{r['section']}: {r['result']}")
    elif a == "build":
        build(project)
    elif a == "verify":
        return verify(project, args.section, whole=args.whole)
    return 0


if __name__ == "__main__":                       # the detached per-section loop
    if len(sys.argv) != 3:
        print("usage: python -m pharos.orchestration.paper <project> <section>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(section_loop(sys.argv[1], sys.argv[2]))


def tex_engine() -> Optional[str]:
    """``PHAROS_TEX_ENGINE`` if it resolves, else the first of ``pdflatex`` /
    ``tectonic`` on PATH; ``None`` when the host has no TeX at all."""
    override = os.environ.get("PHAROS_TEX_ENGINE")
    return next((c for c in ([override] if override else ["pdflatex", "tectonic"])
                 if shutil.which(c)), None)


def tex_compile(engine: str, cwd: Path, main: str) -> Optional[str]:
    """Compile ``main`` in ``cwd`` (two passes for pdflatex, one for tectonic).
    Returns ``None`` on success, else the last lines of the engine's output."""
    cmd = ([engine, "-interaction=nonstopmode", main] if os.path.basename(engine) == "pdflatex"
           else [engine, main])
    for _ in range(2 if os.path.basename(engine) == "pdflatex" else 1):
        cp = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
        if cp.returncode != 0:
            return "\n".join((cp.stdout + cp.stderr).splitlines()[-20:])
    return None
