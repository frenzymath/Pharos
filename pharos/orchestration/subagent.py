"""Launch a main-agent helper in its own session home.

    pharos sub <project> "PROMPT…"          # allocate the next subagents/subN
    pharos sub <project>/subN "PROMPT…"     # reuse an existing helper's home

Each helper has a ``.codex-home`` with shared configuration links. Run one
``codex exec`` in the foreground and log output to ``logs/<timestamp>.log``.
"""

from __future__ import annotations

import subprocess
import sys
import time

from pharos import codex

from ..execution.scaffold import ensure_subagent


def run(target: str, prompt: str) -> int:
    """Provision the helper's home and run one codex session in it."""
    if not prompt.strip():
        print('pharos sub needs a question: pharos sub <project>[/subN] "…"', file=sys.stderr)
        return 2
    project, _, name = target.partition("/")

    sdir = ensure_subagent(project, name or None)
    log_path = sdir / "logs" / f"{time.strftime('%Y%m%dT%H%M%S')}.log"
    print(f"[pharos sub] home: {sdir}")
    print(f"[pharos sub] log:  {log_path}")

    codex_bin = codex.resolve_bin()
    cmd = codex.exec_cmd(
        codex_bin, codex.model(), codex.effort(),
        "-C", str(sdir),
        # Subagent homes are outside Git repositories.
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "-",                                   # the prompt arrives on stdin
    )
    with open(log_path, "w", encoding="utf-8") as logf:
        completed = subprocess.run(
            codex.low_priority(cmd), input=prompt, text=True, stdout=logf,
            stderr=subprocess.STDOUT,
            cwd=str(sdir),
            env=codex.subprocess_env(codex_bin, codex_home=sdir / ".codex-home"),
        )
    return completed.returncode
