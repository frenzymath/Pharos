"""Worker-loop tests using local subprocess stubs and mocked rounds."""

from __future__ import annotations

import json
import os
import signal
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from pharos.execution import layout as L
from pharos.execution import loop
from pharos.tests.util import env


@contextmanager
def _restore_sigterm():
    """main() installs a SIGTERM handler; save/restore so tests don't leak it."""
    old = signal.getsignal(signal.SIGTERM)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, old)


@contextmanager
def _rounds(fn, **env_kw):
    """Run a main-loop test: run_round replaced by ``fn``, SIGTERM restored,
    PHAROS_ROUND_BEAT=0 plus any caps from ``env_kw``."""
    orig = loop.run_round
    loop.run_round = fn
    try:
        with _restore_sigterm(), env(PHAROS_ROUND_BEAT="0", **env_kw):
            yield
    finally:
        loop.run_round = orig


def _mk_worker(tmp: Path, name: str = "xhigh") -> L.WorkerLayout:
    wl = L.WorkerLayout(tmp / "proj" / "workers" / name)
    wl.dir.mkdir(parents=True)
    return wl


def _fake_codex(tmp: Path, body: str) -> Path:
    p = tmp / "fake_codex"
    p.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    p.chmod(0o755)
    return p


def _state(wl: L.WorkerLayout) -> dict:
    return json.loads(wl.status.read_text())


def test_run_round_rc_timeout_missing_and_codex_home(tmp: Path):
    wl = _mk_worker(tmp)
    log = wl.dir / "round.log"
    role = {"MODEL": "m", "REASONING_EFFORT": "xhigh"}

    # child's CODEX_HOME is the worker's own store; rc passes through
    fake = _fake_codex(tmp, "import os,sys\n"
                            "sys.stdout.write(os.environ.get('CODEX_HOME',''))\n"
                            "sys.exit(3)\n")
    with env(PHAROS_CODEX_BIN=str(fake)):
        assert loop.run_round(wl, role, "prompt", log, hard_timeout=30) == 3
    assert log.read_text() == str(wl.codex_home)
    assert loop._Child.proc is None                     # cleared in finally

    # hard timeout: terminate -> 124
    fake = _fake_codex(tmp, "import time\ntime.sleep(60)\n")
    with env(PHAROS_CODEX_BIN=str(fake)):
        assert loop.run_round(wl, role, "prompt", log, hard_timeout=1) == 124
    assert "hard-timeout after 1s" in log.read_text()

    # Missing executables return 127 and record the command.
    with env(PHAROS_CODEX_BIN=str(tmp / "no_such_codex")):
        assert loop.run_round(wl, role, "prompt", log, hard_timeout=30) == 127
    assert "codex binary not found" in log.read_text()


def test_main_stops_on_stop_flag(tmp: Path):
    wl = _mk_worker(tmp)
    wl.stop.touch()
    with _rounds(lambda *a, **k: 0):
        assert loop.main(str(wl.dir)) == 0
    assert not wl.stop.exists()                         # consumed
    assert _state(wl)["state"] == "stopped"


def test_main_stops_on_deadline(tmp: Path):
    wl = _mk_worker(tmp)
    (wl.project_dir / L.DEADLINE_FILE).write_text("1")  # epoch 1 = long past
    with _rounds(lambda *a, **k: 0):
        assert loop.main(str(wl.dir)) == 0
    assert _state(wl)["state"] == "deadline"


def test_main_max_rounds_cap(tmp: Path):
    wl = _mk_worker(tmp)
    calls = []
    with _rounds(lambda *a, **k: (calls.append(1) or 0),
                 PHAROS_MAX_ROUNDS="2"):
        assert loop.main(str(wl.dir)) == 0
    assert len(calls) == 2
    assert _state(wl)["state"] == "max_rounds" and _state(wl)["round"] == 2


def test_main_failed_rounds_back_off_but_never_bail(tmp: Path):
    wl = _mk_worker(tmp)
    slept = []

    def _fail(w, role, prompt, log_path, ht):
        log_path.write_text('"fact_id": "0123456789abcdef"\n')
        return 5
    with _rounds(_fail, PHAROS_MAX_ROUNDS="4", PHAROS_FAIL_BACKOFF_CAP="3"), \
         mock.patch.dict(os.environ, {"PHAROS_ROUND_BEAT": "1"}), \
         mock.patch.object(loop.time, "sleep", slept.append):
        assert loop.main(str(wl.dir)) == 0
    st = _state(wl)
    assert st["state"] == "max_rounds" and st["consec_fail"] == 4
    assert slept == [2, 3, 3, 3]                    # 1*2^k, capped at 3


def test_main_timeout_rc124_does_not_count_as_failure(tmp: Path):
    # a run of hard-timeouts is not a failure streak: no backoff
    wl = _mk_worker(tmp)
    with _rounds(lambda *a, **k: 124, PHAROS_MAX_ROUNDS="3"):
        assert loop.main(str(wl.dir)) == 0
    assert _state(wl)["state"] == "max_rounds" and _state(wl)["consec_fail"] == 0


def test_main_sigterm_handler(tmp: Path):
    wl = _mk_worker(tmp)
    fake_proc = object()

    def _round(w, role, prompt, log_path, ht):
        loop._Child.proc = fake_proc
        os.kill(os.getpid(), signal.SIGTERM)
        raise AssertionError("SIGTERM handler did not exit")

    try:
        with _rounds(_round), mock.patch.object(loop, "_end_group") as end_group:
            try:
                loop.main(str(wl.dir))
                raise AssertionError("handler should sys.exit(0)")
            except SystemExit as e:
                assert e.code == 0
            end_group.assert_called_once_with(fake_proc, grace=3.0)
    finally:
        loop._Child.proc = None
    assert _state(wl)["state"] == "terminated"


def test_write_status_corrupt_existing_recovers(tmp: Path):
    wl = _mk_worker(tmp)
    wl.status.write_text("{not json")
    loop.write_status(wl, state="running")
    assert _state(wl)["state"] == "running" and _state(wl)["worker"] == "xhigh"


def test_kickoff_is_one_pointer_at_the_contract():
    # conduct lives in the worker's AGENTS.md, never in the launch prompt
    p = loop.kickoff("ProjX", "wkrY")
    assert "wkrY" in p and "ProjX" in p and "AGENTS.md" in p
