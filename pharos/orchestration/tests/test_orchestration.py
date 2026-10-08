"""Offline tests for pharos.orchestration — the ``pharos`` CLI verbs.

Filesystem verbs (new/assign/status/list) are deterministic. The loop tests are
integration: they spawn the real ``python -m pharos.execution`` loop subprocess but
stub codex with a fake shell binary (``PHAROS_CODEX_BIN``) so nothing real is
invoked and no API is spent. All processes are force-cleaned in ``finally``.

"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

from pharos.execution import layout as L
from pharos.orchestration import cli, workers
from pharos.tests.util import env as _env


@contextmanager
def _project_env(tmp: Path, **extra):
    """Agents root + stub worker contract/skills so tests never touch the repo's
    agents/ tree; merge any extra env (codex stub, round vars)."""
    contract = tmp / "worker.md"
    contract.write_text("# worker contract (stub)\n", encoding="utf-8")
    skills = tmp / "skills"
    skills.mkdir(exist_ok=True)
    env = {"PHAROS_AGENTS_ROOT": str(tmp / "agents"),
           "PHAROS_WORKER_CONTRACT": str(contract),
           "PHAROS_WORKER_SKILLS": str(skills)}
    env.update(extra)
    with _env(**env):
        yield


def _fake_codex(d: Path) -> Path:
    """A stub codex: print a round marker, sleep FAKE_CODEX_SLEEP, exit 0."""
    p = d / "fake_codex.sh"
    p.write_text('#!/usr/bin/env bash\necho "fake codex round"\n'
                 'sleep "${FAKE_CODEX_SLEEP:-0}"\nexit 0\n')
    p.chmod(0o755)
    return p


def _wait_until(pred, timeout=15.0, interval=0.05) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(interval)
    return pred()


def _st(project: str, worker: str) -> dict:
    return cli.worker_status(L.WorkerLayout(L.worker_dir(project, worker)))


def test_verify_up_refuses_a_held_port_and_port_verb_moves_it(tmp: Path):
    """A port held by a foreign process fails `verify up` before any spawn, with
    the remedy in the message; `pharos verify port` moves the project; while the
    service is up the move is refused."""
    import socket
    import pytest
    from pharos.orchestration import services
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0)); s.listen(1)
    held = s.getsockname()[1]
    try:
        with _project_env(tmp, PHAROS_RUNTIME=str(tmp / "runtime")):
            cli.do_new("P", roles="xhigh:1", port=None)
            services_pid = services._pidfile(services.verify_service_name("P"))
            # pretend P's service sits on the held port
            import json as _json
            meta_path = L.project_dir("P") / "project.json"
            meta = _json.loads(meta_path.read_text()); meta["verify_port"] = held
            meta_path.write_text(_json.dumps(meta))
            r = services.verify_up("P")
            assert r["result"].startswith("FAILED: port") and "pharos verify port P" in r["result"]
            assert not services_pid.exists()
            # move it: refused while "up", allowed when down
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.bind(("127.0.0.1", 0)); free = s2.getsockname()[1]; s2.close()
            services_pid.parent.mkdir(parents=True, exist_ok=True)
            services_pid.write_text(str(os.getpid()))          # alive: this test process
            with pytest.raises(SystemExit, match="is up"):
                services.verify_set_port("P", free)
            services_pid.unlink()
            assert cli.main(["verify", "port", "P", str(free)]) == 0
            assert _json.loads(meta_path.read_text())["verify_port"] == free
    finally:
        s.close()


def _kill_project(project: str):
    try:
        cli.do_stop(project, force=True)
    except SystemExit:
        pass
    for d in L.target_worker_dirs(project):
        pid = workers._read_pid(L.WorkerLayout(d))
        if pid:
            try:
                os.waitpid(pid, os.WNOHANG)
            except (ChildProcessError, OSError):
                pass


def test_assign_replace_and_rejects(tmp: Path):
    with _project_env(tmp):
        cli.do_new("P", roles="xhigh:1")
        cli.do_assign("P/xhigh", "explore direction 3: the symplectic-rank route")
        assert L.WorkerLayout(L.worker_dir("P", "xhigh")).task.read_text() == \
            "explore direction 3: the symplectic-rank route\n"
        cli.do_assign("P/xhigh", "switch to direction 5")   # replace, not append
        assert L.WorkerLayout(L.worker_dir("P", "xhigh")).task.read_text() == "switch to direction 5\n"
        for bad in ["P", "P/nope"]:
            try:
                cli.do_assign(bad, "x")
                assert False, f"should reject {bad!r}"
            except SystemExit:
                pass
        try:
            cli.do_assign("P/xhigh", "   ")
            assert False, "should reject empty task"
        except SystemExit:
            pass
        # status before any start: not alive, created
        s = _st("P", "xhigh")
        assert s["alive"] is False and s["state"] == "created" and s["label"] == "created"


def test_list(tmp: Path):
    with _project_env(tmp):
        cli.do_new("P", roles="xhigh:2", model="gpt-6-astra")
        cli.do_new("Q", roles="max:1", model="gpt-x")
        rows = {r["project"]: r for r in cli.do_list()}
        assert rows["P"]["workers"] == 2 and rows["P"]["live"] == 0 and rows["P"]["model"] == "gpt-6-astra"
        assert rows["Q"]["workers"] == 1 and rows["Q"]["model"] == "gpt-x"


def test_loop_runs_rounds_then_exits(tmp: Path):
    fc = _fake_codex(tmp)
    with _project_env(tmp, PHAROS_CODEX_BIN=str(fc), PHAROS_ROUND_BEAT="0",
                      PHAROS_MAX_ROUNDS="2", FAKE_CODEX_SLEEP="0"):
        cli.do_new("P", roles="xhigh:1")
        try:
            res = cli.do_start("P/xhigh")
            assert res[0]["result"] == "started"
            assert _wait_until(lambda: not _st("P", "xhigh")["alive"]), "loop should exit at backstop"
            s = _st("P", "xhigh")
            assert s["state"] == "max_rounds" and s["round"] == 2
            wl = L.WorkerLayout(L.worker_dir("P", "xhigh"))
            assert (wl.logs / "round_1.log").exists() and (wl.logs / "round_2.log").exists()
        finally:
            _kill_project("P")


def test_graceful_stop(tmp: Path):
    fc = _fake_codex(tmp)
    with _project_env(tmp, PHAROS_CODEX_BIN=str(fc), PHAROS_ROUND_BEAT="0.1",
                      PHAROS_MAX_ROUNDS="0", FAKE_CODEX_SLEEP="0.1"):
        cli.do_new("P", roles="xhigh:1")
        try:
            cli.do_start("P/xhigh")
            assert _wait_until(lambda: _st("P", "xhigh")["round"] >= 1), "should start a round"
            assert _st("P", "xhigh")["alive"] is True
            r = cli.do_stop("P/xhigh")            # graceful
            assert "graceful" in r[0]["result"]
            assert _wait_until(lambda: not _st("P", "xhigh")["alive"]), "loop should exit after .stop"
            assert workers._read_pid(L.WorkerLayout(L.worker_dir("P", "xhigh"))) is None  # pid cleaned
        finally:
            _kill_project("P")


def test_idempotent_start_then_force_stop(tmp: Path):
    fc = _fake_codex(tmp)
    with _project_env(tmp, PHAROS_CODEX_BIN=str(fc), PHAROS_ROUND_BEAT="0",
                      PHAROS_MAX_ROUNDS="0", FAKE_CODEX_SLEEP="30"):
        cli.do_new("P", roles="xhigh:1")
        try:
            assert cli.do_start("P/xhigh")[0]["result"] == "started"
            assert _wait_until(lambda: _st("P", "xhigh")["state"] == "running")
            assert cli.do_start("P/xhigh")[0]["result"] == "already-running"
            r = cli.do_stop("P/xhigh", force=True)
            assert r[0]["result"] == "killed"
            assert _wait_until(lambda: not _st("P", "xhigh")["alive"], timeout=8), "force kills fast"
        finally:
            _kill_project("P")


def test_project_wide_targets(tmp: Path):
    fc = _fake_codex(tmp)
    with _project_env(tmp, PHAROS_CODEX_BIN=str(fc), PHAROS_ROUND_BEAT="0",
                      PHAROS_MAX_ROUNDS="1", FAKE_CODEX_SLEEP="0"):
        cli.do_new("P", roles="xhigh:2")
        try:
            res = cli.do_start("P")              # whole project
            assert {r["worker"] for r in res} == {"xhigh", "xhigh2"}
            assert _wait_until(lambda: all(not _st("P", w)["alive"] for w in ("xhigh", "xhigh2")))
            assert len(cli.do_status("P")) == 2
        finally:
            _kill_project("P")


def test_missing_codex_returns_error_state(tmp: Path):
    with _project_env(tmp, PHAROS_CODEX_BIN="/nonexistent/codex-bin",
                      PHAROS_ROUND_BEAT="0", PHAROS_MAX_ROUNDS="0"):
        cli.do_new("P", roles="xhigh:1")
        try:
            cli.do_start("P/xhigh")
            # rc 127 => loop must not spin; it errors out immediately
            assert _wait_until(lambda: not _st("P", "xhigh")["alive"]), "loop should exit on missing codex"
            s = _st("P", "xhigh")
            assert s["state"] == "error"
        finally:
            _kill_project("P")
