"""Verifier command, run-directory allocation, and subprocess tests using local stubs."""

from __future__ import annotations

import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

from pharos.tests.util import env as _env
from pharos.verify import launcher

_STMT = "For every integer n, n + 0 equals n."
_PROOF = "Zero is the additive identity; adding it changes nothing, so n + 0 = n."


def _write_stub(dirpath: Path, name: str, body: str) -> Path:
    p = dirpath / name
    p.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return p


# stub that writes a valid verification.json to the prompt's output path
_STUB_OK = """\
import re, sys, json
from pathlib import Path
prompt = sys.stdin.read()
out = Path(re.search(r'this exact path:\\s*(\\S+)', prompt).group(1).rstrip('.'))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"verification_report": {"critical_errors": []},
                           "verdict": "correct", "repair_hints": ""}))
print("ok")
"""

# stub that exits nonzero and writes nothing
_STUB_FAIL = "import sys\nsys.stderr.write('boom\\n')\nsys.exit(7)\n"

# stub that sleeps long enough to trip a 1s timeout
_STUB_SLOW = "import time\ntime.sleep(10)\n"


@contextmanager
def _service(stub_body: str, *, timeout: str = "0"):
    """Point the launcher at a stub codex + isolated results/home dirs."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        stub = _write_stub(tmpd, "fake.py", stub_body)
        with _env(PHAROS_CODEX_BIN=str(stub), CODEX_BIN=None,
                  VERIFIER_RESULTS_DIR=str(tmpd / "runs"),
                  VERIFY_AGENT_HOME=str(tmpd / "home"),
                  CODEX_TIMEOUT_SECONDS=timeout):
            (tmpd / "home").mkdir(exist_ok=True)
            yield


def test_build_codex_command_shape():
    with tempfile.TemporaryDirectory() as tmp:
        with _env(PHAROS_CODEX_BIN="/abs/codex",
                  VERIFY_AGENT_HOME=str(tmp),
                  PHAROS_VERIFY_MODEL="m-test", PHAROS_VERIFY_EFFORT="e-test",
                  PHAROS_CODEX_MODEL=None, PHAROS_CODEX_EFFORT=None):
            cmd = launcher.build_codex_command()
    assert cmd[0] == "/abs/codex" and cmd[1] == "exec"
    assert "--model" in cmd and cmd[cmd.index("--model") + 1] == "m-test"
    assert '--config' in cmd and 'model_reasoning_effort="e-test"' in cmd
    assert "-C" in cmd  # agent home
    # gateway injected via -c with role=verifier
    assert "-c" in cmd
    assert any('mcp_servers.pharos=' in a and 'PHAROS_ROLE="verifier"' in a for a in cmd)
    assert "--dangerously-bypass-approvals-and-sandbox" in cmd
    assert cmd[-1] == "-"
    prompt = launcher.build_prompt("RID", _STMT, _PROOF)
    assert prompt.endswith("verification.json.")
    assert "Run_id: RID" in prompt and _STMT in prompt and _PROOF in prompt
    # Large proofs are sent over stdin.
    big = "x" * 500_000
    assert all(big not in arg for arg in cmd)
    assert big in launcher.build_prompt("RID-long", _STMT, big)


def test_allocate_run_id_retries_on_collision():
    with tempfile.TemporaryDirectory() as tmp:
        with _env(VERIFIER_RESULTS_DIR=str(Path(tmp) / "runs")):
            base = launcher.generate_run_id(_STMT)
            root = launcher._results_root()
            root.mkdir(parents=True, exist_ok=True)
            # Force a collision with an existing run directory.
            (root / base).mkdir()
            # generate_run_id is timestamp-based; freeze it so the retry collides
            # deterministically on `base`.
            orig = launcher.generate_run_id
            launcher.generate_run_id = lambda s: base  # type: ignore[assignment]
            try:
                rid = launcher._allocate_run_id(_STMT)
            finally:
                launcher.generate_run_id = orig  # type: ignore[assignment]
            assert rid == f"{base}_2"
            assert (root / rid).is_dir()


def _run(rid="RID"):
    return launcher.run_codex_verification(rid, _STMT, _PROOF)


def test_run_success_reads_back_payload():
    with _service(_STUB_OK):
        out = _run()
        assert out["verdict"] == "correct"
        assert out["verification_report"]["critical_errors"] == []


def test_run_timeout_504():
    with _service(_STUB_SLOW, timeout="1"):
        try:
            _run()
            assert False, "expected 504"
        except HTTPException as e:
            assert e.status_code == 504 and "timed out" in e.detail


def test_run_nonzero_exit_500():
    with _service(_STUB_FAIL):
        try:
            _run()
            assert False, "expected 500"
        except HTTPException as e:
            assert e.status_code == 500 and "exit code 7" in e.detail


def test_ensure_agent_home_provisions_missing_home():
    with tempfile.TemporaryDirectory(prefix="verify_home_") as d:
        home = Path(d) / "agent"
        with _env(VERIFY_AGENT_HOME=str(home)):
            got = launcher.ensure_agent_home()
            assert got == home.resolve()
            agents_md = home / "AGENTS.md"
            skills = home / ".agents" / "skills"
            assert agents_md.exists(), "AGENTS.md must be provisioned"
            assert skills.exists(), ".agents/skills must be provisioned"
            assert agents_md.resolve() == (launcher._REPO_ROOT / "agents" / "contracts" / "verifier.md").resolve()
            assert skills.resolve() == (launcher._REPO_ROOT / "agents" / "skills" / "verify").resolve()
            launcher.ensure_agent_home()
            assert agents_md.exists() and skills.exists()
