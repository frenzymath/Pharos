"""Write a report in a fresh session under ``<project>/reporter/``.

Run in the foreground, log output to ``reporter/logs/``, and list new files
under ``human_report/md/`` and ``human_report/pdf/``. Reports use the current
fact graph without resuming an earlier reporter conversation.
"""

from __future__ import annotations

import subprocess
import time

from pharos import codex
from pharos.execution import layout as L
from pharos.execution.scaffold import ensure_reporter_home

_PROMPT = "Read AGENTS.md and produce the report now."


def run(project: str) -> int:
    home = ensure_reporter_home(project)
    log_path = home / "logs" / f"{time.strftime('%Y%m%dT%H%M%S')}.log"

    codex_bin = codex.resolve_bin()
    cmd = codex.exec_cmd(
        codex_bin, codex.model(), codex.effort(),
        "-C", str(home),
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "-",
    )
    launched_at = time.time()
    with open(log_path, "w", encoding="utf-8") as logf:
        completed = subprocess.run(
            cmd, input=_PROMPT, text=True, stdout=logf, stderr=subprocess.STDOUT,
            cwd=str(home), env=codex.subprocess_env(codex_bin, codex_home=home / ".codex-home"),
        )

    print(f"[pharos report] log: {log_path}")
    for kind in ("md", "pdf"):
        for f in sorted((L.human_report_dir(project) / kind).glob("*")):
            if f.is_file() and f.stat().st_mtime >= launched_at:
                print(f"[pharos report] wrote: {f}")
    return completed.returncode
