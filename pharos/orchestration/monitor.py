"""Append project liveness and resource samples to ``monitor.jsonl``.

Samples include worker and service status, process-group I/O, host load and
pressure, disk throughput and capacity, and recent API errors. The monitor
observes processes without restarting them. ``PHAROS_MONITOR_INTERVAL`` sets
the interval in seconds (default 120).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from pharos.execution import layout as L

_PSI_SOME = re.compile(r"^some .*avg60=([0-9.]+)", re.M)


def _psi60(resource: str) -> Optional[float]:
    """The ``some avg60`` pressure-stall share (%) for ``io``/``cpu``/``memory``
    — the fraction of the last minute in which tasks stalled on that resource.
    ``None`` where /proc/pressure is unavailable."""
    try:
        m = _PSI_SOME.search(Path(f"/proc/pressure/{resource}").read_text())
    except OSError:
        return None
    return float(m.group(1)) if m else None


# whole-disk devices only — partitions (sda1) and dm-* would double-count
_DISK_RE = re.compile(r"^(sd[a-z]+|vd[a-z]+|xvd[a-z]+|nvme\d+n\d+|mmcblk\d+)$")


def _disk_bytes() -> Optional[tuple]:
    """Cumulative (bytes_read, bytes_written) summed over the real disks."""
    try:
        lines = Path("/proc/diskstats").read_text().splitlines()
    except OSError:
        return None
    r = w = 0
    for ln in lines:
        f = ln.split()
        if len(f) >= 10 and _DISK_RE.match(f[2]):
            r += int(f[5]) * 512                 # sectors are 512B in diskstats
            w += int(f[9]) * 512
    return r, w


def _io_rate(window: float = 1.0) -> Dict:
    """Live disk throughput (MB/s), measured over a short window."""
    a = _disk_bytes()
    if a is None:
        return {"io_read_mbps": None, "io_write_mbps": None}
    time.sleep(window)
    b = _disk_bytes()
    return {"io_read_mbps": round((b[0] - a[0]) / window / 2**20, 2),
            "io_write_mbps": round((b[1] - a[1]) / window / 2**20, 2)}


def _group_io(pgid: int) -> Dict:
    """Sum disk I/O for a worker's process group from ``/proc/<pid>/io``."""
    rd = wr = 0
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            if os.getpgid(int(pid_dir.name)) != pgid:
                continue
            for line in (pid_dir / "io").read_text().splitlines():
                if line.startswith("read_bytes:"):
                    rd += int(line.split()[1])
                elif line.startswith("write_bytes:"):
                    wr += int(line.split()[1])
        except (OSError, ValueError):
            continue
    return {"io_read_mb": round(rd / 2**20, 1), "io_write_mb": round(wr / 2**20, 1)}


def sample(project: str) -> Dict:
    """Read one project status and resource sample."""
    from . import services
    from .cli import worker_status
    from .health import _recent_api_failures

    workers = []
    for w in L.list_workers(project):
        st = worker_status(L.WorkerLayout(L.worker_dir(project, w)))
        row = {k: st[k] for k in ("worker", "alive", "state", "round", "label", "active_at")}
        if st["alive"]:
            row.update(_group_io(st["pid"]))      # the loop's pid is its group id
        workers.append(row)
    try:
        verify_state = services.verify_health(project)["state"]
    except SystemExit:
        verify_state = "unknown"
    return {
        "ts": int(time.time()),
        "workers": workers,
        "main_up": services.main_status([project])[0]["running"],
        "verify": verify_state,
        "load1": round(os.getloadavg()[0], 2),
        "io60": _psi60("io"),
        "cpu60": _psi60("cpu"),
        **_io_rate(),
        "disk_free_gb": round(shutil.disk_usage(L.project_dir(project)).free / 2**30, 1),
        "api_errors": _recent_api_failures(limit=20, project=project),
    }


def record(project: str) -> Dict:
    """Take one sample and append it to the project's monitor.jsonl."""
    row = sample(project)
    path = L.project_dir(project) / "monitor.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def run(project: str) -> None:
    interval = int(os.environ.get("PHAROS_MONITOR_INTERVAL", "120"))
    while True:
        try:
            record(project)
        except Exception as exc:  # Keep the monitor running after a failed sample.
            print(f"[monitor] sample failed: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m pharos.orchestration.monitor <project>", file=sys.stderr)
        raise SystemExit(2)
    run(sys.argv[1])
