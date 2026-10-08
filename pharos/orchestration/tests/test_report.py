"""Offline test for ``pharos report``: a python stub stands in for codex."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pharos.execution.scaffold import do_new
from pharos.orchestration import report
from pharos.tests.util import env

_STUB = """#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path

home = Path.cwd()
record = Path(os.environ["STUB_ARGV_LOG"])
with record.open("a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv) + "\\n")
print("CODEX_HOME=" + os.environ.get("CODEX_HOME", ""))
md = home.parent / "human_report" / "md"
md.mkdir(parents=True, exist_ok=True)
(md / f"stub_{time.time_ns()}.md").write_text("# stub report\\n")
"""


def _project(tmp: Path) -> Path:
    contract = tmp / "worker.md"
    contract.write_text("# stub\n")
    (tmp / "skills").mkdir(exist_ok=True)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"),
             PHAROS_WORKER_CONTRACT=str(contract),
             PHAROS_WORKER_SKILLS=str(tmp / "skills"),
             PHAROS_VERIFY_URL=None, VERIFY_PORT=None):
        do_new("P", roles="xhigh:1")
    return tmp / "agents" / "P"


def test_report_fresh_session_writes_and_never_resumes(tmp: Path):
    pdir = _project(tmp)
    stub = tmp / "codex_stub.py"
    stub.write_text(_STUB, encoding="utf-8")
    stub.chmod(0o755)
    argv_log = tmp / "argv.log"

    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(stub),
             STUB_ARGV_LOG=str(argv_log)):
        assert report.run("P") == 0
        time.sleep(1.05)                          # distinct per-second log names
        assert report.run("P") == 0

    logs = sorted((pdir / "reporter" / "logs").glob("*.log"))
    assert len(logs) == 2
    home_marker = "CODEX_HOME=" + str(pdir / "reporter" / ".codex-home")
    assert home_marker in logs[0].read_text() and home_marker in logs[1].read_text()

    runs = [json.loads(l) for l in argv_log.read_text().splitlines()]
    assert len(runs) == 2
    assert all("resume" not in argv for argv in runs)

    md_files = list((pdir / "human_report" / "md").glob("*.md"))
    assert len(md_files) == 2
