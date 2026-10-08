"""CLI dispatch, process bookkeeping, and directory-scope tests with stub workers."""

from __future__ import annotations

import io
import json
import os
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pharos.execution import layout as L
from pharos.orchestration import cli, scope, services, workers
from pharos.tests.util import env, expect_exit


@contextmanager
def _project_env(tmp: Path, **extra):
    contract = tmp / "worker.md"
    contract.write_text("# worker contract (stub)\n", encoding="utf-8")
    skills = tmp / "skills"
    skills.mkdir(exist_ok=True)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"),
             PHAROS_WORKER_CONTRACT=str(contract),
             PHAROS_WORKER_SKILLS=str(skills), **extra):
        yield


@contextmanager
def _patch_spawn():
    """Record spawn calls; return our own pid so the worker reads as alive."""
    calls = []

    def fake(wdir):
        calls.append(Path(wdir))
        return os.getpid()

    orig = workers.spawn_loop
    workers.spawn_loop = fake
    try:
        yield calls
    finally:
        workers.spawn_loop = orig


def _wl(project: str, worker: str) -> L.WorkerLayout:
    return L.WorkerLayout(L.worker_dir(project, worker))


def _run_main(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(argv)
    return rc, buf.getvalue()


def test_alive_permission_error_means_alive():
    # a pid we can't signal (root's pid 1) exists but isn't ours -> alive
    if os.geteuid() == 0:
        return
    assert workers._alive(1) is True


def test_alive_zombie_is_dead(tmp: Path):
    # an exited-but-unreaped child answers kill(pid,0) yet is effectively dead;
    # /proc's Z state must win
    import subprocess
    import time
    proc = subprocess.Popen(["true"])
    try:
        pid = proc.pid

        def is_zombie():
            try:
                stat = Path(f"/proc/{pid}/stat").read_text()
                return stat.rsplit(")", 1)[1].split()[0] == "Z"
            except (OSError, IndexError):
                return False

        end = time.time() + 5
        while time.time() < end and not is_zombie():
            time.sleep(0.02)
        assert is_zombie(), "child did not become a zombie"
        assert workers._alive(pid) is False
    finally:
        proc.wait()


def test_start_is_idempotent_and_clears_stale_stop(tmp: Path):
    with _project_env(tmp), _patch_spawn() as calls:
        cli.do_new("P", roles="xhigh:1")
        wl = _wl("P", "xhigh")
        wl.stop.touch()                                   # stale flag
        assert cli.do_start("P/xhigh") == [{"worker": "xhigh", "result": "started"}]
        assert calls == [wl.dir] and not wl.stop.exists()
        assert workers._read_pid(wl) == os.getpid()
        # second start sees the live pid -> no second spawn
        assert cli.do_start("P/xhigh")[0]["result"] == "already-running"
        assert len(calls) == 1


def test_start_locked_when_lock_held(tmp: Path):
    import fcntl
    with _project_env(tmp), _patch_spawn():
        cli.do_new("P", roles="xhigh:1")
        wl = _wl("P", "xhigh")
        held = open(wl.lock, "w")
        fcntl.flock(held, fcntl.LOCK_EX)
        try:
            assert workers._start_one(wl) == "locked"
        finally:
            fcntl.flock(held, fcntl.LOCK_UN)
            held.close()


def test_stop_graceful_touches_stop_flag(tmp: Path):
    with _project_env(tmp):
        cli.do_new("P", roles="xhigh:1")
        wl = _wl("P", "xhigh")
        wl.pid.write_text(str(os.getpid()))               # "alive" (our pid)
        assert workers._stop_one(wl, force=False) == "stopping (graceful)"
        assert wl.stop.exists()
        wl.stop.unlink()


def test_parser_and_task_sources():
    p = cli.build_parser()
    a = p.parse_args(["new", "P", "--roles", "xhigh:2", "--model", "m"])
    assert (a.cmd, a.project, a.roles, a.model) == ("new", "P", "xhigh:2", "m")
    assert p.parse_args(["assign", "P/xhigh", "--task", "t"]).task == "t"
    assert p.parse_args(["stop", "P", "--force"]).force is True
    expect_exit(p.parse_args, [])                         # subcommand required

    class Args:
        task = file = None
        stdin = False
    assert "one of --task" in str(expect_exit(cli._task_from_args, Args()))
    Args.task = "direct"
    assert cli._task_from_args(Args()) == "direct"


def test_main_dispatch_roundtrip(tmp: Path):
    with _project_env(tmp), _patch_spawn():
        rc, out = _run_main(["new", "P", "--roles", "xhigh:2", "--model", "m"])
        assert rc == 0 and "created P with 2 workers" in out
        rc, out = _run_main(["list", "--json"])
        assert json.loads(out)[0]["workers"] == 2
        rc, out = _run_main(["assign", "P/xhigh", "--task", "prove lemma 4"])
        assert rc == 0 and _wl("P", "xhigh").task.read_text() == "prove lemma 4\n"
        rc, out = _run_main(["start", "P/xhigh"])
        assert rc == 0 and "started" in out
        rc, out = _run_main(["status", "P/xhigh", "--json"])
        assert json.loads(out)[0]["worker"] == "xhigh"
        rc, out = _run_main(["stop", "P/xhigh"])
        assert rc == 0 and "graceful" in out
        _wl("P", "xhigh").stop.unlink(missing_ok=True)


def test_main_start_pins_project_env_inside_tmux_command(tmp: Path):
    """A shared tmux server must not leak its first project's session home."""
    with _project_env(tmp, PHAROS_CODEX_MODEL="global-model"):
        cli.do_new("P", roles="high:1", model="project-model")
        results = [
            SimpleNamespace(returncode=1, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ]
        with patch.object(services.subprocess, "run", side_effect=results) as run:
            services.main_start("P", tag="pp")

        launch = run.call_args_list[1].args[0]
        assert f"CODEX_HOME={L.main_codex_home('P')}" in launch
        assert "PHAROS_CODEX_MODEL=project-model" in launch


def test_sub_verb_provisions_and_runs(tmp: Path):
    """Subagents receive the prompt on stdin and reuse a named session home."""
    fake = tmp / "fake_codex"
    fake.write_text("#!/usr/bin/env python3\n"
                    "import sys, os\n"
                    "sys.stdout.write('HOME=' + os.environ.get('CODEX_HOME','') + '\\n')\n"
                    "sys.stdout.write('PROMPT=' + sys.stdin.read())\n", encoding="utf-8")
    fake.chmod(0o755)
    with _project_env(tmp, PHAROS_VERIFY_URL=None, VERIFY_PORT=None,
                      PHAROS_CODEX_BIN=str(fake)):
        cli.do_new("p_sub", roles="xhigh:1")
        assert cli.main(["sub", "p_sub", "why", "is", "X", "true?"]) == 0
        home = tmp / "agents" / "p_sub" / "subagents" / "sub1"
        body = next((home / "logs").glob("*.log")).read_text()
        assert f"HOME={home / '.codex-home'}" in body
        assert "PROMPT=why is X true?" in body
        assert cli.main(["sub", "p_sub/sub1", "follow up"]) == 0    # reuse, not sub2
        assert not (home.parent / "sub2").exists()
        assert cli.main(["sub", "p_sub"]) == 2                      # question required


def test_chat_launches_with_full_permissions(tmp: Path, monkeypatch):
    """The foreground chat uses the same non-interactive permission mode as
    the resident main agent while keeping its separate chat home."""
    with _project_env(tmp, PHAROS_VERIFY_URL=None, VERIFY_PORT=None,
                      PHAROS_CODEX_BIN="/fake/codex"):
        cli.do_new("p_chat", roles="xhigh:1")
        calls = {}
        original_cwd = Path.cwd()

        def fake_execvp(binary, argv):
            calls["binary"] = binary
            calls["argv"] = argv
            raise RuntimeError("exec captured")

        monkeypatch.setattr(cli.os, "execvp", fake_execvp)
        try:
            cli.main(["chat", "p_chat"])
        except RuntimeError as exc:
            assert str(exc) == "exec captured"
        else:
            raise AssertionError("chat should replace the process with codex")
        finally:
            os.chdir(original_cwd)

        assert calls == {
            "binary": "/fake/codex",
            "argv": ["/fake/codex", "--dangerously-bypass-approvals-and-sandbox"],
        }


def test_scope_by_directory(tmp: Path):
    with _project_env(tmp, PHAROS_VERIFY_URL=None, VERIFY_PORT=None):
        cli.do_new("P", roles="xhigh:1")
    pdir = tmp / "agents" / "P"
    assert scope.current(tmp) == (scope.OPS, None)
    assert scope.current(pdir) == (scope.MAIN, "P")
    assert scope.current(pdir / "workers" / "xhigh") == (scope.NONE, "P")

    for verb in ("new", "list", "main", "doctor"):                # ops-only
        assert "ops agent" in str(expect_exit(scope.check, verb, pdir))
    assert scope.check("status", pdir) == (scope.MAIN, "P")
    for verb in ("status", "assign"):
        assert "not available here" in str(expect_exit(scope.check, verb,
                                                        pdir / "workers" / "xhigh"))
    for verb in ("compute", "usage", "render"):
        assert scope.check(verb, pdir / "workers" / "xhigh") == (scope.NONE, "P")


def test_scope_pins_own_project_refuses_siblings():
    assert scope.pin(None, scope.MAIN, "P", verb="status") == "P"
    assert scope.pin("xhigh", scope.MAIN, "P", verb="assign", need_worker=True) == "P/xhigh"
    assert "only on its own project" in str(
        expect_exit(scope.pin, "Other/xhigh", scope.MAIN, "P", verb="stop"))
    assert "needs a target" in str(
        expect_exit(scope.pin, None, scope.OPS, None, verb="status"))
