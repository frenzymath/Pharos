"""Tests for runtime paths, project scaffolding, and process-group termination."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from pharos.execution import layout as L
from pharos.execution import loop, scaffold
from pharos.tests.util import env as _env


@contextmanager
def _project_env(tmp: Path):
    """Point the agents root + worker contract/skills at tmp stubs so the tests
    are self-contained (no dependency on the repo's agents/ tree existing)."""
    contract = tmp / "worker.md"
    contract.write_text("# worker contract (stub)\n", encoding="utf-8")
    skills = tmp / "skills"
    skills.mkdir(exist_ok=True)
    with _env(PHAROS_AGENTS_ROOT=str(tmp / "agents"),
              PHAROS_WORKER_CONTRACT=str(contract),
              PHAROS_WORKER_SKILLS=str(skills)):
        yield


def test_parse_roles_default_roster():
    pairs = L.parse_roles("xhigh:3,max:4")
    names = [n for n, _ in pairs]
    assert names == ["xhigh", "xhigh2", "xhigh3", "max", "max2", "max3", "max4"]
    # base role (digits stripped) drives reasoning effort
    assert [b for _, b in pairs] == ["xhigh"] * 3 + ["max"] * 4
    assert dict(pairs)["xhigh2"] == "xhigh" and dict(pairs)["max4"] == "max"


def test_parse_roles_rejects_bad_specs():
    for bad in ["", "   ", "xhigh:0", "xhigh", "xhigh:abc", ":3", "3:xhigh"]:
        try:
            L.parse_roles(bad)
            assert False, f"should reject {bad!r}"
        except ValueError:
            pass


def test_worker_layout_paths():
    wl = L.WorkerLayout(Path("/x/proj/workers/xhigh"))
    assert wl.name == "xhigh" and wl.project == "proj"
    assert wl.project_dir == Path("/x/proj")
    assert wl.task.name == L.TASK_FILE and wl.role.name == L.ROLE_FILE
    assert wl.pid.name == L.PID_FILE and wl.lock.name == L.LOCK_FILE
    assert wl.stop.name == L.STOP_FILE and wl.status.name == L.STATUS_FILE
    assert wl.logs.name == L.LOGS_DIR
    assert wl.codex_config == Path("/x/proj/workers/xhigh/.codex/config.toml")


def test_resolve_and_target():
    assert L.resolve_target("proj") == ("proj", None)
    assert L.resolve_target("proj/xhigh") == ("proj", "xhigh")
    assert L.resolve_target("/proj/xhigh/") == ("proj", "xhigh")


def test_agents_root_default_is_self_located_not_cwd_relative(tmp: Path):
    """A side actor runs `pharos usage` from <project>/reporter/ in a bare shell;
    the default must not become <project>/reporter/runtime/projects."""
    here = Path.cwd()
    try:
        os.chdir(tmp)
        with _env(PHAROS_AGENTS_ROOT=None, PHAROS_RUNTIME=None):
            assert L.agents_root() == (L.repo_root() / "runtime" / "projects").resolve()
        with _env(PHAROS_AGENTS_ROOT=None, PHAROS_RUNTIME=str(tmp / "rt")):
            assert L.agents_root() == (tmp / "rt" / "projects").resolve()
        with _env(PHAROS_AGENTS_ROOT=str(tmp / "elsewhere"), PHAROS_RUNTIME=str(tmp / "rt")):
            assert L.agents_root() == (tmp / "elsewhere").resolve()
    finally:
        os.chdir(here)


def _held_port():
    """A listening socket on a free loopback port; the caller closes it."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    return s, s.getsockname()[1]


def test_allocate_verify_port_skips_a_port_the_host_holds(tmp: Path):
    s, held = _held_port()
    try:
        with _project_env(tmp), _env(VERIFY_PORT=str(held)):
            got = scaffold.allocate_verify_port()
            assert got != held and got > held
            assert scaffold.port_is_free(got)
    finally:
        s.close()


def test_do_new_with_a_held_port_is_refused(tmp: Path):
    import pytest
    s, held = _held_port()
    try:
        with _project_env(tmp):
            with pytest.raises(SystemExit, match="held by another process"):
                scaffold.do_new("P", roles="xhigh:1", port=held)
            assert not L.project_dir("P").exists()
    finally:
        s.close()


def test_do_new_with_an_explicit_free_port_and_set_verify_port(tmp: Path):
    import pytest
    s, free = _held_port()
    s.close()                          # now free
    with _project_env(tmp):
        r = scaffold.do_new("P", roles="xhigh:1", port=free)
        assert r["verify_port"] == free
        assert json.loads((L.project_dir("P") / "project.json").read_text())["verify_port"] == free
        # a sibling may not take the same port
        with pytest.raises(SystemExit, match="already project 'P'"):
            scaffold.do_new("Q", roles="xhigh:1", port=free)
        # moving P to another free port rewrites project.json; the worker's
        # gateway URL follows at the next config write
        s2, free2 = _held_port(); s2.close()
        moved = scaffold.set_verify_port("P", free2)
        assert moved["old_port"] == free and moved["verify_port"] == free2
        assert json.loads((L.project_dir("P") / "project.json").read_text())["verify_port"] == free2
        wl = L.WorkerLayout(L.worker_dir("P", "xhigh"))
        scaffold.write_codex_config(wl)
        assert f"127.0.0.1:{free2}/verify" in wl.codex_config.read_text()


def test_do_new_scaffolds_project(tmp: Path):
    with _project_env(tmp):
        r = scaffold.do_new("P", roles="xhigh:2,max:1")
        assert r["workers"] == ["xhigh", "xhigh2", "max"]
        pdir = L.project_dir("P")
        assert (pdir / "global_memory").is_dir() and (pdir / "fact_graph").is_dir()
        meta = json.loads((pdir / "project.json").read_text())
        assert meta["workers"] == ["xhigh", "xhigh2", "max"] and meta["model"] == "gpt-6-astra"

        for w, eff in [("xhigh", "xhigh"), ("xhigh2", "xhigh"), ("max", "max")]:
            wl = L.WorkerLayout(L.worker_dir("P", w))
            assert wl.local_memory.is_dir() and wl.logs.is_dir()
            # symlinks resolve to the (stub) contract + skills
            assert (wl.dir / "AGENTS.md").resolve() == L.worker_md().resolve()
            assert (wl.dir / ".agents" / "skills").resolve() == L.worker_skills_dir().resolve()
            cfg = wl.codex_config.read_text()
            assert 'PHAROS_ROLE = "worker"' in cfg
            assert 'args = ["-m", "pharos.gateway"]' in cfg  # pinned MCP launch
            assert "tool_timeout_sec = 100000" in cfg
            assert 'PHAROS_VERIFY_TIMEOUT = "90000"' in cfg
            assert f'PHAROS_AUTHOR = "{w}"' in cfg and str(pdir) in cfg
            role = wl.role.read_text()
            assert f"REASONING_EFFORT={eff}" in role and "MODEL=gpt-6-astra" in role
            assert "(unassigned" in wl.task.read_text()
            assert json.loads(wl.status.read_text())["state"] == "created"


def test_do_new_refuses_existing(tmp: Path):
    with _project_env(tmp):
        scaffold.do_new("P", roles="xhigh:1")
        try:
            scaffold.do_new("P")
            assert False, "should refuse an existing project dir"
        except SystemExit:
            pass


def test_do_new_env_overrides_reach_worker_config(tmp: Path):
    with _project_env(tmp):
        with _env(PHAROS_VERIFY_URL="http://127.0.0.1:9999/verify",
                  PHAROS_VERIFY_TIMEOUT="1234"):
            scaffold.do_new("Q", roles="xhigh:1")
        cfg = L.WorkerLayout(L.worker_dir("Q", "xhigh")).codex_config.read_text()
        assert 'PHAROS_VERIFY_URL = "http://127.0.0.1:9999/verify"' in cfg
        assert 'PHAROS_VERIFY_TIMEOUT = "1234"' in cfg          # a TOML string


# A "codex" that ignores SIGTERM and has a grandchild that ignores it too;
# both record their pids so the test can see whether they are gone.
_STUBBORN = """import os, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = subprocess.Popen([sys.executable, "-c",
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(300)"])
open(sys.argv[-1], "w").write(f"{os.getpid()} {child.pid}")
time.sleep(300)
"""


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_for(path: Path):
    for _ in range(100):
        if path.is_file() and path.read_text().strip():
            return [int(x) for x in path.read_text().split()]
        time.sleep(0.1)
    raise AssertionError("stub never started")


def test_end_group_kills_a_tree_that_ignores_sigterm(tmp: Path):
    pids = tmp / "pids"
    proc = subprocess.Popen([sys.executable, "-c", _STUBBORN, str(pids)], start_new_session=True)
    parent, child = _wait_for(pids)
    loop._end_group(proc, grace=0.5)
    assert not _alive(parent) and not _alive(child)
    try:
        os.killpg(proc.pid, 0)
        assert False, "the process group still has members"
    except ProcessLookupError:
        pass


def test_run_round_hard_timeout_ends_the_whole_tree(tmp: Path):
    stub = tmp / "codex.py"
    stub.write_text("#!/usr/bin/env python3\n" + _STUBBORN)
    stub.chmod(0o755)
    pids = tmp / "pids"
    with _project_env(tmp), _env(PHAROS_CODEX_BIN=str(stub)):
        scaffold.do_new("P", roles="xhigh:1")
        wl = L.WorkerLayout(L.worker_dir("P", "xhigh"))
        log = tmp / "round.log"
        # the stub takes the pid file as its last argument, in place of the prompt
        rc = loop.run_round(wl, loop._read_role(wl), str(pids), log, hard_timeout=1)
    assert rc == 124 and "hard-timeout" in log.read_text()
    parent, child = _wait_for(pids)
    assert not _alive(parent) and not _alive(child)


def test_deadline_passed(tmp: Path):
    pdir = tmp / "proj"
    pdir.mkdir()
    assert loop._deadline_passed(pdir) is False           # no deadline file
    (pdir / L.DEADLINE_FILE).write_text("1")              # epoch 1 = long past
    assert loop._deadline_passed(pdir) is True
    (pdir / L.DEADLINE_FILE).write_text("garbage")        # bad = not passed
    assert loop._deadline_passed(pdir) is False


def test_write_status_atomic_and_stamps(tmp: Path):
    wl = L.WorkerLayout(tmp / "proj" / "workers" / "xhigh")
    wl.dir.mkdir(parents=True)
    loop.write_status(wl, state="running", round=2)
    st = json.loads(wl.status.read_text())
    assert st["state"] == "running" and st["round"] == 2
    assert st["worker"] == "xhigh" and st["pid"] == os.getpid() and "updated_at" in st
    # merge, not overwrite: a second write keeps prior fields
    loop.write_status(wl, last_rc=0)
    st2 = json.loads(wl.status.read_text())
    assert st2["round"] == 2 and st2["last_rc"] == 0


def test_read_role_defaults_and_overrides(tmp: Path):
    wl = L.WorkerLayout(tmp / "proj" / "workers" / "max")
    wl.dir.mkdir(parents=True)
    # no .role -> the dedicated worker model, independent of the neutral model
    with _env(PHAROS_WORKER_MODEL=None, PHAROS_CODEX_MODEL=None):
        role = loop._read_role(wl)
    assert role["MODEL"] == "gpt-6-astra" and role["ROLE"] == "xhigh" and role["PHAROS_AUTHOR"] == "max"
    # the worker-specific setting wins over the neutral model
    with _env(PHAROS_WORKER_MODEL="worker-model", PHAROS_CODEX_MODEL="neutral-model"):
        role = loop._read_role(wl)
    assert role["MODEL"] == "worker-model"
    wl.role.write_text("# comment\nMODEL=gpt-x\nREASONING_EFFORT=max\n\nROLE=max\n")
    role = loop._read_role(wl)
    assert role["MODEL"] == "gpt-x" and role["REASONING_EFFORT"] == "max" and role["ROLE"] == "max"


def test_do_new_allocates_sequential_verify_ports(tmp: Path, monkeypatch):
    monkeypatch.setattr(scaffold, "port_is_free", lambda *a, **k: True)  # the host may hold 8091+
    with _env(PHAROS_AGENTS_ROOT=str(tmp), PHAROS_VERIFY_URL=None, VERIFY_PORT=None):
        r1 = scaffold.do_new("p_one", roles="xhigh:1")
        r2 = scaffold.do_new("p_two", roles="xhigh:1")
    assert r1["verify_port"] == 8091 and r2["verify_port"] == 8092
    meta = json.loads((tmp / "p_one" / "project.json").read_text())
    assert meta["verify_port"] == 8091
    # the worker MCP env pins the project's own verifier URL
    cfg = (tmp / "p_one" / "workers" / "xhigh" / ".codex" / "config.toml").read_text()
    assert 'PHAROS_VERIFY_URL = "http://127.0.0.1:8091/verify"' in cfg
    cfg2 = (tmp / "p_two" / "workers" / "xhigh" / ".codex" / "config.toml").read_text()
    assert 'PHAROS_VERIFY_URL = "http://127.0.0.1:8092/verify"' in cfg2


def test_do_new_provisions_project_main_home(tmp: Path):
    with _env(PHAROS_AGENTS_ROOT=str(tmp), PHAROS_VERIFY_URL=None, VERIFY_PORT=None):
        scaffold.do_new("p_main", roles="xhigh:1")
    pdir = tmp / "p_main"
    # Project main-agent resources are distinct from deployment operator resources.
    assert (pdir / "AGENTS.md").resolve() == L.main_md().resolve()
    assert (pdir / "OPERATOR.md").resolve() == (L.repo_root() / "OPERATOR.md").resolve()
    assert (pdir / ".agents" / "skills").resolve() == L.main_skills_dir().resolve()
    assert L.main_md().resolve() != (L.repo_root() / "AGENTS.md").resolve()
    assert L.main_skills_dir().resolve() != (L.repo_root() / ".agents" / "skills").resolve()
    cfg = (pdir / ".codex" / "config.toml").read_text()
    assert 'PHAROS_ROLE = "main"' in cfg and str(pdir) in cfg
    assert 'args = ["-m", "pharos.gateway"]' in cfg
    assert (pdir / ".codex-home").is_dir()            # main agent's own sessions
    vdir = pdir / "verifier"
    assert (vdir / "AGENTS.md").resolve() == L.verifier_md().resolve()
    assert (vdir / ".agents" / "skills").resolve() == L.verify_skills_dir().resolve()
    assert (vdir / ".codex-home").is_dir()
    assert (vdir / "runs").is_dir()
    assert (pdir / "subagents").is_dir()
    # one session home per kind of side actor, plus the report artifact dirs
    for adhoc in ("reporter", "chat"):
        assert (pdir / adhoc / ".codex-home").is_dir()
    assert (pdir / "human_report" / "md").is_dir()
    assert (pdir / "human_report" / "pdf").is_dir()
    # the chat home is a main-agent-role cwd of its own: contract + pinned MCP
    assert (pdir / "chat" / "AGENTS.md").resolve().name == "chat.md"
    chat_cfg = (pdir / "chat" / ".codex" / "config.toml").read_text()
    assert 'PHAROS_ROLE = "main"' in chat_cfg and str(pdir) in chat_cfg
    assert (pdir / "expert_guidance").is_dir()
    assert (pdir / "expert_guidance" / "INSTRUCTIONS.md").is_file()
    assert (pdir / "expert_guidance" / "GUIDANCE.md").is_file()
    assert "No instructions yet" in (pdir / "expert_guidance" / "GUIDANCE.md").read_text()
    assert (pdir / "checkpoints").is_dir()
    assert (pdir / "literature" / "papers").is_dir() and (pdir / "literature" / "notes").is_dir()
    assert (pdir / "materials").is_dir()
    # style/: the paper's style layer — `default` -> the default style package,
    # README.md copied from it (when the package ships one)
    sdir = pdir / "style"
    assert sdir.is_dir()
    assert (sdir / "default").is_symlink()
    assert (sdir / "default").resolve() == L.default_style_dir().resolve()
    if (L.default_style_dir() / "README.md").is_file():
        assert (sdir / "README.md").is_file()
    assert (pdir / "workers" / "xhigh" / ".codex-home").is_dir()


def test_paper_template_prefers_the_projects_own(tmp: Path):
    with _env(PHAROS_AGENTS_ROOT=str(tmp)):
        assert L.style_dir("S") == tmp / "S" / "style"
        default = L.default_style_dir() / L.STYLE_TEMPLATE
        assert L.paper_template("S") == default               # no style/ yet
        own = L.style_dir("S") / L.STYLE_TEMPLATE
        own.parent.mkdir(parents=True)
        assert L.paper_template("S") == default               # style/ but no template
        own.write_text("%%SECTIONS%%\n")
        assert L.paper_template("S") == own


def test_ensure_paper_workspace_copies_the_projects_own_template(tmp: Path):
    with _project_env(tmp):
        scaffold.do_new("T", roles="xhigh:1")
        own = L.style_dir("T") / L.STYLE_TEMPLATE
        own.write_text("\\title{%%TITLE%%}\n%%SECTIONS%%\n")
        scaffold.ensure_paper_workspace("T")
        local = L.paper_src_dir("T") / "template.tex"
        assert local.read_text() == "\\title{%%TITLE%%}\n%%SECTIONS%%\n"
        # copied once: a later change to style/TEMPLATE.tex never overwrites
        # the copy the main agent edits
        own.write_text("changed\n")
        scaffold.ensure_paper_workspace("T")
        assert local.read_text() == "\\title{%%TITLE%%}\n%%SECTIONS%%\n"


def test_ensure_paper_workspace_falls_back_to_the_default_template(tmp: Path):
    with _project_env(tmp):
        scaffold.do_new("U", roles="xhigh:1")
        # Missing style files are provisioned when the paper workspace is opened.
        sdir = L.style_dir("U")
        (sdir / "default").unlink()
        shutil.rmtree(sdir)
        scaffold.ensure_paper_workspace("U")
        assert (sdir / "default").resolve() == L.default_style_dir().resolve()
        scaffold.ensure_paper_workspace("U")                  # idempotent
        default = L.default_style_dir() / L.STYLE_TEMPLATE
        local = L.paper_src_dir("U") / "template.tex"
        if default.is_file():
            assert local.read_text() == default.read_text()
        else:
            assert not local.exists()


def test_ensure_subagent_allocates_and_validates(tmp: Path):
    with _env(PHAROS_AGENTS_ROOT=str(tmp), PHAROS_VERIFY_URL=None, VERIFY_PORT=None):
        scaffold.do_new("p_sub", roles="xhigh:1")
        s1 = scaffold.ensure_subagent("p_sub")
        s2 = scaffold.ensure_subagent("p_sub")
        assert s1.name == "sub1" and s2.name == "sub2"
        assert (s1 / ".codex-home").is_dir() and (s1 / "logs").is_dir()
        # explicit reuse is idempotent
        assert scaffold.ensure_subagent("p_sub", "sub1") == s1
        # bad names and unknown projects are refused
        for bad in ("lit-review", "sub0", "../x", "sub"):
            try:
                scaffold.ensure_subagent("p_sub", bad)
                assert False, f"should reject {bad!r}"
            except SystemExit:
                pass
        try:
            scaffold.ensure_subagent("no_such_project")
            assert False, "should reject unknown project"
        except SystemExit:
            pass
