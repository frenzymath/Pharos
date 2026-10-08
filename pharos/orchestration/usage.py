"""Aggregate project token usage, elapsed time, and monitor history.

The last ``total_token_usage`` event in each session provides its cumulative
usage. Optional ``PHAROS_PRICE_INPUT``, ``PHAROS_PRICE_CACHED``, and
``PHAROS_PRICE_OUTPUT`` values (USD per million tokens) enable cost estimates.
Project timestamps come from ``project.json``; liveness and load history come
from ``monitor.jsonl``.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

from pharos.execution import layout as L

_USAGE_RE = re.compile(r'"total_token_usage":\s*(\{[^{}]*\})')
# token_count events recur through a session, so the last one sits near EOF —
# but the final assistant message (after it) can be large; read a generous tail.
_TAIL_BYTES = 256 * 1024


def _session_total(path: Path) -> Optional[Dict]:
    """The final cumulative ``total_token_usage`` of one session file."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - _TAIL_BYTES))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    hits = _USAGE_RE.findall(tail)
    if not hits:
        return None
    try:
        return json.loads(hits[-1])
    except json.JSONDecodeError:
        return None


_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens",
         "total_tokens", "sessions")


def _zero() -> Dict:
    return {k: 0 for k in _KEYS}


def home_usage(codex_home: Path) -> Dict:
    """Sum the sessions of one agent home."""
    total = _zero()
    if not (codex_home / "sessions").is_dir():
        return total
    for f in sorted((codex_home / "sessions").rglob("*.jsonl")):
        u = _session_total(f)
        if not u:
            continue
        total["sessions"] += 1
        for k in ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens"):
            total[k] += int(u.get(k, 0) or 0)
    return total


def _cost_usd(u: Dict) -> Optional[float]:
    prices = [os.environ.get(k) for k in
              ("PHAROS_PRICE_INPUT", "PHAROS_PRICE_CACHED", "PHAROS_PRICE_OUTPUT")]
    if not any(prices):
        return None
    p_in, p_cached, p_out = (float(p or 0) for p in prices)
    fresh = u["input_tokens"] - u["cached_input_tokens"]
    return (fresh * p_in + u["cached_input_tokens"] * p_cached
            + u["output_tokens"] * p_out) / 1_000_000


def _monitor_summary(project: str) -> Optional[Dict]:
    path = L.project_dir(project) / "monitor.jsonl"
    if not path.is_file():
        return None
    rows: List[Dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        return None
    deaths: Dict[str, int] = {}
    prev: Dict[str, bool] = {}
    for r in rows:
        for w in r.get("workers", []):
            name, alive = w.get("worker"), bool(w.get("alive"))
            if prev.get(name) and not alive:
                deaths[name] = deaths.get(name, 0) + 1
            prev[name] = alive

    def _peak(key: str) -> Optional[float]:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return max(vals) if vals else None

    last = rows[-1]
    return {"samples": len(rows), "first_ts": rows[0]["ts"], "last_ts": last["ts"],
            "worker_deaths": deaths, "load1": last.get("load1"),
            "load1_max": _peak("load1"), "io60": last.get("io60"),
            "io60_max": _peak("io60"), "cpu60": last.get("cpu60"),
            "cpu60_max": _peak("cpu60"),
            "io_read_mbps": last.get("io_read_mbps"),
            "io_read_mbps_max": _peak("io_read_mbps"),
            "io_write_mbps": last.get("io_write_mbps"),
            "io_write_mbps_max": _peak("io_write_mbps"),
            "api_errors": last.get("api_errors"),
            "disk_free_gb": last.get("disk_free_gb"), "verify": last.get("verify"),
            "main_up": last.get("main_up")}


def project_usage(project: str) -> Dict:
    """Everything ``pharos usage`` reports, as one dict."""
    pdir = L.project_dir(project)
    if not (pdir / "project.json").is_file():
        raise SystemExit(f"no such project: {project}")
    meta = json.loads((pdir / "project.json").read_text(encoding="utf-8"))

    groups: Dict[str, Dict] = {"main": home_usage(L.main_codex_home(project))}
    workers = {w: home_usage(L.WorkerLayout(L.worker_dir(project, w)).codex_home)
               for w in L.list_workers(project)}
    groups["workers"] = {k: sum(w[k] for w in workers.values()) for k in _KEYS}
    groups["verifier"] = home_usage(L.verifier_codex_home(project))
    subs = sorted(p for p in L.subagents_dir(project).glob("sub*") if p.is_dir()) \
        if L.subagents_dir(project).is_dir() else []
    sub_usages = [home_usage(s / ".codex-home") for s in subs]
    groups["subagents"] = {k: sum(su[k] for su in sub_usages) for k in _KEYS}
    total = {k: sum(g[k] for g in groups.values()) for k in _KEYS}
    from .compute import _dir_size_gb
    comp = L.computation_dir(project)
    out = {
        "project": project,
        "created_at": meta.get("created_at"),
        "last_started_at": meta.get("last_started_at"),
        "computation_gb": round(_dir_size_gb(comp), 2) if comp.is_dir() else None,
        "age_days": round((time.time() - meta["created_at"]) / 86400, 2)
        if isinstance(meta.get("created_at"), (int, float)) else None,
        "tokens": {**{g: groups[g] for g in groups}, "total": total},
        "per_worker": workers,
        "cost_usd": _cost_usd(total),
        "monitor": _monitor_summary(project),
    }
    return out


def _fmt_tok(n: int) -> str:
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(n)


def format_usage(u: Dict) -> str:
    lines = [f"== pharos usage: {u['project']} =="]
    if u["age_days"] is not None:
        lines.append(f"  age: {u['age_days']} days (created "
                     f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(u['created_at']))})")
    for g in ("main", "workers", "verifier", "subagents", "total"):
        t = u["tokens"][g]
        lines.append(f"  {g:<10} {t['sessions']:>4} sessions  "
                     f"in {_fmt_tok(t['input_tokens']):>8} "
                     f"(cached {_fmt_tok(t['cached_input_tokens'])})  "
                     f"out {_fmt_tok(t['output_tokens']):>7}")
    if u["cost_usd"] is not None:
        lines.append(f"  cost: ${u['cost_usd']:.2f} (PHAROS_PRICE_* per 1M tokens)")
    if u.get("computation_gb") is not None:
        cap = os.environ.get("PHAROS_COMPUTE_DIR_CAP_GB", "20")
        lines.append(f"  computation/: {u['computation_gb']}G of the {cap}G cap")
    m = u["monitor"]
    if m:
        span_h = (m["last_ts"] - m["first_ts"]) / 3600
        deaths = ", ".join(f"{k}×{v}" for k, v in m["worker_deaths"].items()) or "none"
        lines.append(f"  monitor: {m['samples']} samples over {span_h:.1f}h; "
                     f"worker deaths: {deaths}")
        lines.append(f"    pressure last/max: io {m['io60']}/{m['io60_max']}%, "
                     f"cpu {m['cpu60']}/{m['cpu60_max']}%, "
                     f"load {m['load1']}/{m['load1_max']}; "
                     f"io rate last/max: read {m['io_read_mbps']}/{m['io_read_mbps_max']} "
                     f"write {m['io_write_mbps']}/{m['io_write_mbps_max']} MB/s; "
                     f"api errors {m['api_errors']}")
        lines.append(f"    last: disk {m['disk_free_gb']}G free, "
                     f"verify {m['verify']}, main {'up' if m['main_up'] else 'down'}")
    else:
        lines.append("  monitor: no samples (pharos monitor up <project>)")
    return "\n".join(lines)
