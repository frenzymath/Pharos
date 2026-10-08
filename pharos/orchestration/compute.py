"""Run project computation with per-job limits and a shared systemd slice.

The ``pharos-compute.slice`` configuration caps the deployment at 4 CPUs and
16G memory. ``--heavy`` raises per-job limits to the slice limits. Without a
systemd user session, the fallback applies a memory rlimit and low CPU
priority; it cannot enforce the collective cap.

Scripts run from ``<project>/computation/``. Launch is refused when that
directory exceeds ``PHAROS_COMPUTE_DIR_CAP_GB`` (default 20 GiB).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

_SLICE = "pharos-compute.slice"


def _tier(heavy: bool) -> dict:
    e = os.environ.get
    if heavy:
        return {"mem": e("PHAROS_COMPUTE_HEAVY_MEM", "16G"),
                "cpu": e("PHAROS_COMPUTE_HEAVY_CPU", "400%"),
                "seconds": int(e("PHAROS_COMPUTE_HEAVY_SECONDS", "7200"))}
    return {"mem": e("PHAROS_COMPUTE_MEM", "2G"),
            "cpu": e("PHAROS_COMPUTE_CPU", "100%"),
            "seconds": int(e("PHAROS_COMPUTE_SECONDS", "600"))}


def resolve_computation_dir(script: Path) -> Path:
    """Resolve the project computation directory and require the script inside it."""
    script = script.resolve()
    for parent in script.parents:
        if (parent / "project.json").is_file() and (parent / "workers").is_dir():
            comp = parent / "computation"
            if comp in script.parents:
                return comp
            raise SystemExit(
                f"computation scripts live in {comp} (move {script.name} there — "
                "scripts and their outputs stay in the one capped folder)")
    raise SystemExit(f"{script} is not inside a Pharos project")


def _dir_size_gb(path: Path) -> float:
    out = subprocess.run(["du", "-sb", str(path)], capture_output=True, text=True)
    try:
        return int(out.stdout.split()[0]) / 2**30
    except (ValueError, IndexError):
        return 0.0


def _check_dir_cap(comp: Path) -> None:
    cap = float(os.environ.get("PHAROS_COMPUTE_DIR_CAP_GB", "20"))
    size = _dir_size_gb(comp)
    if size >= cap:
        raise SystemExit(
            f"{comp} holds {size:.1f}G, over its {cap:g}G cap — delete stale "
            "scripts/results before computing again (the cap protects the host)")


def _systemd_available() -> bool:
    if os.environ.get("PHAROS_COMPUTE_NO_SYSTEMD"):
        return False
    if not shutil.which("systemd-run"):
        return False
    probe = subprocess.run(["systemd-run", "--user", "--scope", "--quiet",
                            "--collect", "--", "/bin/true"],
                           capture_output=True)
    return probe.returncode == 0


def _mem_bytes(spec: str) -> int:
    mult = {"K": 2**10, "M": 2**20, "G": 2**30}
    if spec and spec[-1].upper() in mult:
        return int(float(spec[:-1]) * mult[spec[-1].upper()])
    return int(spec)


def _interpreter(script: Path) -> List[str]:
    """Use SageMath for ``.sage``, otherwise ``PHAROS_COMPUTE_PYTHON`` or Python."""
    if script.suffix == ".sage":
        sage = shutil.which("sage")
        if not sage:
            raise SystemExit("*.sage needs SageMath on PATH (not installed)")
        return [sage]
    return [os.environ.get("PHAROS_COMPUTE_PYTHON") or sys.executable]


def run(script: str, args: Optional[List[str]] = None, heavy: bool = False) -> int:
    """Run one computation script under the caps; returns its exit code."""
    spath = Path(script)
    comp = resolve_computation_dir(spath)
    _check_dir_cap(comp)
    tier = _tier(heavy)
    payload = [*_interpreter(spath), str(spath.resolve()), *(args or [])]

    if _systemd_available():
        cmd = ["systemd-run", "--user", "--scope", "--quiet", "--collect",
               f"--slice={_SLICE}",
               "-p", f"MemoryMax={tier['mem']}", "-p", "MemorySwapMax=0",
               "-p", f"CPUQuota={tier['cpu']}", "-p", "TasksMax=128",
               "--", *payload]
        preexec = None
    else:
        print("[pharos compute] WARNING: no systemd user session — per-job "
              "rlimits only; the collective 4-CPU/16G pool cap is NOT enforced",
              file=sys.stderr)
        limit = _mem_bytes(tier["mem"])

        def preexec():                       # child only: cap memory, yield CPU
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
            os.nice(19)
        cmd = payload

    try:
        done = subprocess.run(cmd, cwd=str(comp), preexec_fn=preexec,
                              timeout=tier["seconds"])
    except subprocess.TimeoutExpired:
        print(f"[pharos compute] killed: exceeded the {tier['seconds']}s "
              f"{'heavy' if heavy else 'default'}-tier time cap", file=sys.stderr)
        return 124
    if done.returncode != 0:
        print(f"[pharos compute] exit code {done.returncode}", file=sys.stderr)
    return done.returncode
