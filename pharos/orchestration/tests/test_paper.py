"""Smoke tests for pharos paper — the per-section writer/verifier loop and the
verbs around it. Codex is a python stub (PHAROS_CODEX_BIN) that records argv,
then writes REPORT.md (in a writer home) or VERDICT.md (in a verifier home)
with a controllable status."""

from __future__ import annotations

import stat
import time
from pathlib import Path

from pharos.execution import layout as L
from pharos.execution.scaffold import do_new
from pharos.orchestration import paper
from pharos.tests.util import env

_STUB = """#!/usr/bin/env python3
import os, sys, time
from pathlib import Path
Path("argv.log").open("a").write(repr(sys.argv) + "\\n")
sys.stdin.read()
time.sleep(float(os.environ.get("STUB_SLEEP", "0")))
if Path("TASK.md").is_file() and len(Path("argv.log").read_text().splitlines()) <= int(os.environ.get("STUB_DIE", "0")):
    sys.exit(1)                              # the writer died mid-turn: no new REPORT.md
if not Path("TASK.md").is_file():            # a verifier home
    n = len(Path("argv.log").read_text().splitlines())
    verdicts = os.environ.get("STUB_VERDICTS", "pass").split(",")
    Path("VERDICT.md").write_text("status: " + verdicts[min(n, len(verdicts)) - 1] + "\\n")
else:                                        # a writer home
    Path("section.tex").write_text("\\\\section{S}\\nbody\\n")
    Path("REPORT.md").write_text("status: " + os.environ.get("STUB_STATUS", "done") + "\\n")
"""


def _project(tmp: Path) -> Path:
    stub = tmp / "stub_codex.py"
    stub.write_text(_STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    (tmp / "worker.md").write_text("# stub\n")
    (tmp / "skills").mkdir(exist_ok=True)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_WORKER_CONTRACT=str(tmp / "worker.md"),
             PHAROS_WORKER_SKILLS=str(tmp / "skills"), PHAROS_VERIFY_URL=None, VERIFY_PORT=None):
        do_new("P", roles="xhigh:1")
    return tmp / "agents" / "P" / "paper" / "src" / "sections"


def _settle(project="P", timeout=15.0) -> int:
    return paper.wait(project, [], timeout)


def test_assign_provisions_writer_and_its_verifier(tmp: Path):
    sections = _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents")):
        paper.assign("P", "intro", "write the introduction")
    home = sections / "intro"
    assert (home / "TASK.md").read_text() == "write the introduction\n"
    assert (home / "AGENTS.md").exists() and (home / "verifier" / "AGENTS.md").exists()
    assert (home / ".codex-home").is_dir() and (home / "verifier" / ".codex-home").is_dir()


def test_loop_done_on_first_pass_and_resumes_next_time(tmp: Path):
    sections = _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(tmp / "stub_codex.py")):
        paper.assign("P", "intro", "write it")
        assert paper.start("P", "intro")[0]["result"] == "started"
        assert _settle() == 0
        home = sections / "intro"
        st = paper.status("P")[0]
        assert st["state"] == "done" and st["round"] == 1 and st["verdict"] == "pass"
        assert (home / "logs" / "round_1_write.log").exists()
        assert (home / "verifier" / "logs" / "round_1.log").exists()
        # a second assignment resumes the writer's own session
        (home / ".codex-home" / "sessions").mkdir(parents=True)
        (home / ".codex-home" / "sessions" / "rollout.jsonl").write_text("{}")
        paper.assign("P", "intro", "revise")
        assert paper.start("P", section=None, all_=True)[0]["result"] == "started"
        assert _settle() == 0
        assert "'resume', '--last'" in (home / "argv.log").read_text().splitlines()[-1]
        assert paper.status("P")[0]["round"] == 1          # a fresh loop, round 1 again


def test_loop_revises_until_verifier_passes(tmp: Path):
    _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"),
             STUB_VERDICTS="fail,pass"):
        paper.assign("P", "main", "prove it")
        paper.start("P", "main")
        assert _settle() == 0
        st = paper.status("P")[0]
        assert st["state"] == "done" and st["round"] == 2 and st["verdict"] == "pass"


def test_loop_escalate_and_writer_failed(tmp: Path):
    _project(tmp)
    root = str(tmp / "agents")
    with env(PHAROS_AGENTS_ROOT=root, PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"),
             STUB_STATUS="escalate"):
        paper.assign("P", "hard", "try")
        paper.start("P", "hard")
        assert _settle() == 0
        assert paper.status("P")[0]["state"] == "escalate"
    # no round cap: the loop ends only when the writer itself reports failed
    with env(PHAROS_AGENTS_ROOT=root, PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"),
             STUB_STATUS="failed"):
        paper.assign("P", "stuck", "try")
        paper.start("P", "stuck")
        assert _settle() == 0
        st = [r for r in paper.status("P") if r["name"] == "stuck"][0]
        assert st["state"] == "failed" and st["round"] == 1 and "writer reported failed" in st["note"]


def test_loop_reruns_a_session_that_died_instead_of_reading_a_stale_report(tmp: Path):
    sections = _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"),
             STUB_DIE="1", PHAROS_ROUND_BEAT="0"):
        paper.assign("P", "intro", "write it")
        paper.start("P", "intro")
        assert _settle() == 0
        home = sections / "intro"
        st = paper.status("P")[0]
        assert st["state"] == "done" and st["round"] == 1 and st["verdict"] == "pass"
        assert "retry 1" in st["note"]
        logs = sorted(p.name for p in (home / "logs").glob("round_1_write*.log"))
        assert logs == ["round_1_write.log", "round_1_write.retry1.log"]
        # the verifier ran once, after the rerun — never on the stale section
        assert len((home / "verifier" / "argv.log").read_text().splitlines()) == 1


def test_wait_returns_at_the_attention_round(tmp: Path):
    _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"),
             STUB_VERDICTS="fail", PHAROS_PAPER_ATTENTION_ROUNDS="2"):
        paper.assign("P", "long", "try")
        paper.start("P", "long")
        assert paper.wait("P", ["long"], timeout=30) == 0          # returned at round 2, loop alive
        st = [r for r in paper.status("P") if r["name"] == "long"][0]
        assert st["state"].startswith("running") and st["round"] >= 2 and "review" in st["note"]
        assert paper.stop("P", "long")["result"] == "stopped"


def test_wait_returns_when_the_first_running_section_ends(tmp: Path):
    _project(tmp)
    base = dict(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"))
    with env(**base, STUB_SLEEP="30"):
        paper.assign("P", "slow", "take your time")
        paper.start("P", "slow")
    with env(**base, STUB_SLEEP=None):
        paper.assign("P", "fast", "quick")
        paper.start("P", "fast")
        t = time.time()
        assert paper.wait("P", [], timeout=25) == 0        # `fast` ended; `slow` still running
        assert time.time() - t < 20
        states = {r["name"]: r["state"] for r in paper.status("P")}
        assert states["fast"] == "done" and states["slow"].startswith("running")
        assert paper.stop("P", "slow")["result"] == "stopped"


def test_wait_timeout_and_stop(tmp: Path):
    _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"),
             STUB_SLEEP="30"):
        paper.assign("P", "slow", "take your time")
        paper.start("P", "slow")
        assert paper.wait("P", ["slow"], timeout=1) == 124
        assert paper.stop("P", "slow")["result"] == "stopped"
        assert paper.status("P")[0]["state"] == "stopped"


def test_build_assembles_in_order(tmp: Path):
    sections = _project(tmp)
    tpl = tmp / "T.tex"
    tpl.write_text("\\title{%%TITLE%%}\n\\begin{document}\n%%SECTIONS%%\n\\end{document}\n")
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_TEX_ENGINE="no-such-engine"):
        for n in ("02-main", "01-intro"):
            paper.assign("P", n, "x")
            (sections / n / "section.tex").write_text("body\n")
        out = paper.build("P", template=tpl)
    text = out.read_text()
    assert out.name == "main.tex"
    assert text.index("sections/01-intro") < text.index("sections/02-main")
    assert "\\title{P}" in text


def test_build_leaves_placeholders_in_comments_alone(tmp: Path):
    sections = _project(tmp)
    tpl = tmp / "T.tex"
    tpl.write_text("% build fills %%TITLE%% and %%SECTIONS%% here\n\\documentclass{article}\n"
                   "\\title{%%TITLE%%}\n\\begin{document}\n%%SECTIONS%%\n\\end{document}\n")
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_TEX_ENGINE="no-such-engine"):
        for n in ("01-intro", "02-main"):
            paper.assign("P", n, "x")
            (sections / n / "section.tex").write_text("body\n")
        text = paper.build("P", template=tpl).read_text()
    assert text.splitlines()[0] == "% build fills %%TITLE%% and %%SECTIONS%% here"
    assert text.index("\\documentclass") < text.index("\\input{sections/01-intro")
    assert text.count("\\input{sections/") == 2 and "\\title{P}" in text


def test_build_warns_on_a_quad_slip_but_still_builds(tmp: Path, capsys):
    sections = _project(tmp)
    tpl = tmp / "T.tex"
    tpl.write_text("\\begin{document}\n%%SECTIONS%%\n\\end{document}\n")
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_TEX_ENGINE="no-such-engine"):
        paper.assign("P", "01-a", "x")
        (sections / "01-a" / "section.tex").write_text(
            "$x=1,\\qquad y=2$\n"          # fine
            "$x=1,qquad y=2$\n"             # the slip
            "% ,qquad inside a comment\n"   # ignored
            "a quadratic form\n")           # a word, not a slip
        out = paper.build("P", template=tpl)
    lint = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("lint:")]
    assert len(lint) == 1 and "sections/01-a/section.tex:2:" in lint[0]
    assert out.name == "main.tex" and "sections/01-a" in out.read_text()


def test_build_uses_the_projects_own_template(tmp: Path):
    _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_TEX_ENGINE="no-such-engine"):
        paper.ensure_paper_workspace("P")
        local = L.paper_src_dir("P") / "template.tex"
        local.write_text("\\author{Me}\n%%SECTIONS%%\n")   # the main agent's edited copy
        assert "\\author{Me}" in paper.build("P").read_text()


def test_verify_verb_runs_one_round(tmp: Path):
    _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents"), PHAROS_CODEX_BIN=str(tmp / "stub_codex.py"),
             STUB_VERDICTS="fail"):
        paper.assign("P", "s", "x")
        assert paper.verify("P", "s") == 1
        assert paper.verify("P", whole=True) == 1       # whole-paper home, same protocol


def test_wait_returns_promptly_when_nothing_runs(tmp: Path):
    _project(tmp)
    with env(PHAROS_AGENTS_ROOT=str(tmp / "agents")):
        t = time.time()
        assert paper.wait("P", [], timeout=5) == 0
        assert time.time() - t < 2
