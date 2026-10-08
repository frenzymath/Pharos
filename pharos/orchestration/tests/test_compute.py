"""Computation directory checks, rlimit fallback, timeout, and scope tests."""

from __future__ import annotations

from pathlib import Path

from pharos.execution.scaffold import do_new
from pharos.orchestration import compute, scope
from pharos.tests.util import env, expect_exit


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


def test_script_must_live_in_computation_dir(tmp: Path):
    pdir = _project(tmp)
    stray = pdir / "stray.py"
    stray.write_text("print('no')\n")
    assert "computation" in str(expect_exit(compute.resolve_computation_dir, stray))
    inside = pdir / "computation" / "ok.py"
    inside.write_text("print('yes')\n")
    assert compute.resolve_computation_dir(inside) == pdir / "computation"
    outside = tmp / "nowhere.py"
    outside.write_text("print('no')\n")
    assert "not inside a Pharos project" in str(
        expect_exit(compute.resolve_computation_dir, outside))


def test_dir_cap_refuses_launch(tmp: Path):
    pdir = _project(tmp)
    script = pdir / "computation" / "job.py"
    script.write_text("print('x')\n")
    with env(PHAROS_COMPUTE_DIR_CAP_GB="0"):          # any nonempty dir is over
        e = expect_exit(compute.run, str(script))
    assert "cap" in str(e)


def test_run_fallback_rc_cwd_and_timeout(tmp: Path):
    pdir = _project(tmp)
    comp = pdir / "computation"
    ok = comp / "writes.py"
    ok.write_text("import pathlib\npathlib.Path('out.txt').write_text('42')\n"
                  "raise SystemExit(3)\n")
    with env(PHAROS_COMPUTE_NO_SYSTEMD="1"):
        assert compute.run(str(ok)) == 3             # rc passthrough
    assert (comp / "out.txt").read_text() == "42"    # cwd = computation/
    slow = comp / "slow.py"
    slow.write_text("import time\ntime.sleep(30)\n")
    with env(PHAROS_COMPUTE_NO_SYSTEMD="1", PHAROS_COMPUTE_SECONDS="1"):
        assert compute.run(str(slow)) == 124         # time cap kills


def test_compute_is_allowed_everywhere(tmp: Path):
    pdir = _project(tmp)
    assert scope.check("compute", pdir / "workers" / "xhigh")[0] == scope.NONE
    assert scope.check("compute", pdir)[0] == scope.MAIN
    assert scope.check("compute", tmp)[0] == scope.OPS
