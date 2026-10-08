"""Deployment and model-backend health checks.

``check-codex`` probes the configured backend, scans recent worker and verifier
logs, and records results in ``runtime/logs/codex-health.jsonl``. ``doctor``
also checks dependencies and project services.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from pharos import codex
from pharos.execution import layout as L

# Signatures of a backend problem in a round log / verify log.
_API_FAILURE = re.compile(
    r"error sending request|stream disconnected|unexpected status|status 429"
    r"|status 5\d\d|rate limit|too many requests|unauthorized|quota"
    r"|timed out|request failed",
    re.IGNORECASE,
)


def _runtime() -> Path:
    return Path(os.environ.get("PHAROS_RUNTIME") or (L.repo_root() / "runtime"))


def _trace(record: Dict) -> None:
    """Append one JSONL line to the health history (best effort)."""
    logs = _runtime() / "logs"
    try:
        logs.mkdir(parents=True, exist_ok=True)
        with open(logs / "codex-health.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ping() -> Dict:
    """Send a small live request to the configured API endpoint."""
    base = os.environ.get("CODEX_API_BASE_URL", "")
    model = codex.model()
    azure = os.environ.get("CODEX_API_PROVIDER") == "azure"
    key_var = "AZURE_OPENAI_API_KEY" if azure else "OPENAI_API_KEY"
    key = os.environ.get(key_var, "")
    version = os.environ.get("CODEX_API_VERSION", "")
    out: Dict = {"kind": "ping", "model": model}
    if not (base and key):
        out.update(ok=False, err=f"CODEX_API_BASE_URL / {key_var} not set (config/pharos.env)")
        return out
    if azure and not version:
        out.update(ok=False, err="CODEX_API_VERSION not set for Azure (config/pharos.env)")
        return out
    started = time.time()
    try:
        from openai import AzureOpenAI, OpenAI
        client = (AzureOpenAI(base_url=base, api_key=key, api_version=version, timeout=60)
                  if azure else OpenAI(base_url=base, api_key=key, timeout=60))
        with client:
            resp = client.responses.create(model=model, input="ping",
                                           reasoning={"effort": "low"})
        status = getattr(resp, "status", None)
        out.update(ok=(status == "completed"), status=status)
    except Exception as exc:                       # noqa: BLE001 — report, never raise
        out.update(ok=False, err=f"{type(exc).__name__}: {exc}"[:300])
    out["latency_s"] = round(time.time() - started, 2)
    return out


def _login_status() -> Dict:
    """The chatgpt backend has no endpoint to ping; probe the codex login."""
    completed = subprocess.run([codex.resolve_bin(), "login", "status"],
                               capture_output=True, text=True)
    detail = (completed.stdout + completed.stderr).strip().splitlines()
    return {"kind": "login-status", "backend": "chatgpt",
            "ok": completed.returncode == 0,
            "detail": detail[-1] if detail else ""}


def _recent_api_failures(limit: int = 30, project: Optional[str] = None) -> int:
    """How many of the most recent worker/verify logs show an API failure.
    With ``project``, only that project's logs (the monitor samples this)."""
    root = L.agents_root()
    pat = project or "*"
    logs: List[Path] = []
    if root.is_dir():
        logs += list(root.glob(f"{pat}/workers/*/logs/round_*.log"))
        logs += list(root.glob(f"{pat}/verifier/runs/*/log.md"))
    logs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    hits = 0
    for path in logs[:limit]:
        try:
            if _API_FAILURE.search(path.read_text(encoding="utf-8", errors="replace")):
                hits += 1
        except OSError:
            continue
    return hits


def check_codex() -> Dict:
    """Probe the backend + scan recent logs. Returns a result dict; the caller
    prints it. ``ok`` False means the backend did not answer."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if os.environ.get("CODEX_BACKEND", "api") == "chatgpt":
        result = _login_status()
    else:
        result = _ping()
    result["ts"] = stamp
    _trace(result)
    failures = _recent_api_failures()
    _trace({"ts": stamp, "kind": "scan", "recent_logs_with_api_errors": failures})
    result["recent_logs_with_api_errors"] = failures
    return result


def _check(label: str, ok: bool, detail: str = "", soft: bool = False) -> Dict:
    return {"label": label, "state": ("ok" if ok else ("warn" if soft else "FAIL")),
            "detail": detail}


def doctor(probe: bool = False) -> List[Dict]:
    """Check dependencies, backend connectivity, and project service status.

    Backend checks may make an API request and append to the health log.
    ``probe`` additionally renders a PDF, compiles the paper template, and
    queries the literature service. It treats missing config, Node, and
    backend connectivity as failures rather than warnings.
    """
    from .services import verify_health          # local import (services imports cli)

    rows: List[Dict] = []
    root = L.repo_root()

    cfg = root / "config" / "pharos.env"
    rows.append(_check("config/pharos.env", cfg.is_file(),
                       str(cfg) if cfg.is_file() else "missing (copy from .example)",
                       soft=not cfg.is_file() and not probe))

    rows.append(_check("python", True, sys.executable))
    for dep, hard in (("pharos", True), ("mcp", True), ("fastapi", True), ("openai", False)):
        try:
            __import__(dep)
            rows.append(_check(f"python dep: {dep}", True))
        except ImportError as exc:
            rows.append(_check(f"python dep: {dep}", False, str(exc), soft=not hard))

    node = os.environ.get("PHAROS_NODE", "")
    rows.append(_check("node", bool(node) and os.access(node, os.X_OK), node or "not provisioned",
                       soft=not probe))

    codex_bin = codex.resolve_bin()
    version = subprocess.run([codex_bin, "--version"], capture_output=True, text=True)
    rows.append(_check("codex", version.returncode == 0,
                       version.stdout.strip() or "not working (run scripts/bootstrap.sh)"))

    shared = codex.shared_codex_home()
    rows.append(_check("codex config", (shared / "config.toml").is_file(),
                       str(shared / "config.toml") if (shared / "config.toml").is_file()
                       else "missing (scripts/setup-codex.sh)"))

    ping = check_codex()
    rows.append(_check("codex backend", bool(ping.get("ok")),
                       ping.get("err") or f"latency {ping.get('latency_s')}s", soft=not probe))
    if ping.get("recent_logs_with_api_errors"):
        rows.append(_check("recent API errors", False,
                           f"{ping['recent_logs_with_api_errors']} recent log(s) show API failures",
                           soft=True))

    projects = L.list_projects()
    if not projects:
        rows.append(_check("projects", True, "none yet (pharos new <project>)", soft=True))
    for project in projects:
        try:
            health = verify_health(project)
        except SystemExit as exc:
            rows.append(_check(f"verify {project}", False, str(exc)))
            continue
        state, port = health["state"], health["port"]
        rows.append(_check(
            f"verify {project}", state == "ours",
            {"ours": f"up :{port}",
             "foreign": f":{port} answered by a FOREIGN process — port collision",
             "stale": f"down :{port} (stale pidfile)",
             "down": f"down :{port} (pharos verify up {project})"}[state],
            soft=state in ("stale", "down")))

    rows.append(_check("git", bool(shutil.which("git")), soft=True,
                       detail="" if shutil.which("git") else "not on PATH"))
    rows.append(_check("tmux", bool(shutil.which("tmux")),
                       "" if shutil.which("tmux") else
                       "not on PATH — `pharos main start` runs the main agent in tmux (install tmux)"))
    from .render import chrome_bin, mathjax_src
    chrome = chrome_bin()
    mj_vendored = mathjax_src().startswith("file:")
    rows.append(_check("render (chromium)", bool(chrome),
                       chrome or "no chromium/chrome — no human-report PDF can be made "
                                 "(install chromium, or set PHAROS_CHROME_BIN)"))
    rows.append(_check("render (mathjax)", mj_vendored,
                       "vendored" if mj_vendored else
                       "via CDN — an offline host renders no formulas (re-run bootstrap)", soft=True))
    from .paper import tex_engine
    engine = tex_engine()
    rows.append(_check("tex engine", bool(engine),
                       engine or "no pdflatex / tectonic on PATH — `pharos paper build` cannot "
                                 "produce the paper (install texlive, or set PHAROS_TEX_ENGINE)"))
    prio = [t for t in ("ionice", "nice") if not shutil.which(t)]
    rows.append(_check("priority tools", not prio, "" if not prio else
                       f"missing {', '.join(prio)} — workers cannot be deprioritized", soft=True))
    try:
        free_gb = shutil.disk_usage(root / "runtime" if (root / "runtime").exists() else root).free / 1e9
        rows.append(_check("disk free (runtime)", free_gb >= 20, f"{free_gb:.0f} GB", soft=True))
    except OSError:
        pass

    from .compute import _systemd_available
    slice_file = Path.home() / ".config" / "systemd" / "user" / "pharos-compute.slice"
    ok = _systemd_available() and slice_file.is_file()
    rows.append(_check(
        "compute caps", ok,
        f"slice installed ({slice_file})" if ok else
        "no systemd slice — per-job rlimits only; run bootstrap (host-crash risk)",
        soft=True))

    if probe:
        rows.extend(probes(chrome=chrome, engine=engine))
    return rows


def probes(chrome: Optional[str], engine: Optional[str]) -> List[Dict]:
    """Probe PDF rendering, TeX compilation, and literature search.

    Local output files are confined to a temporary directory.
    """
    import tempfile
    rows: List[Dict] = []
    with tempfile.TemporaryDirectory(prefix="pharos-doctor-") as td:
        tdir = Path(td)
        # 1. human report: markdown with a formula -> PDF
        if chrome:
            from .render import render
            md = tdir / "probe.md"
            md.write_text("# Doctor\n\nA formula: $\\int_0^1 x\\,dx = \\tfrac12$.\n", encoding="utf-8")
            try:
                pdf = render(md, tdir / "probe.pdf")
                good = pdf.is_file() and pdf.read_bytes()[:4] == b"%PDF"
                rows.append(_check("probe: render a report PDF", good,
                                   f"{pdf.stat().st_size} bytes" if good else "no PDF came out"))
            except SystemExit as exc:
                rows.append(_check("probe: render a report PDF", False, str(exc)))
        else:
            rows.append(_check("probe: render a report PDF", False, "skipped — no chromium"))
        # 2. the paper: compile the default template as `pharos paper build` would
        if engine:
            from .paper import tex_compile
            tpl = L.default_style_dir() / "TEMPLATE.tex"
            src = tpl.read_text(encoding="utf-8")
            body = "\\section{Doctor}\n\nA formula: $\\int_0^1 x\\,dx = \\tfrac12$.\n"
            src = "".join(ln if ln.lstrip().startswith("%") and not ln.lstrip().startswith("%%SECTIONS%%") else
                          ln.replace("%%SECTIONS%%", body).replace("%%TITLE%%", "Doctor")
                          for ln in src.splitlines(keepends=True))
            (tdir / "main.tex").write_text(src, encoding="utf-8")
            err = tex_compile(engine, tdir, "main.tex")
            good = err is None and (tdir / "main.pdf").is_file()
            rows.append(_check("probe: compile the paper template", good,
                               f"{engine}: every package the template loads is installed" if good
                               else f"{engine} failed — a package the template needs is missing:\n{err}"))
        else:
            rows.append(_check("probe: compile the paper template", False, "skipped — no TeX engine"))
        # 3. the literature service
        from pharos.integrations import matlas
        r = matlas.search("Cauchy-Schwarz inequality", num_results=1, timeout=30)
        rows.append(_check("probe: theorem search (matlas)", not r.get("error"),
                           f"{r.get('endpoint')} answered" if not r.get("error")
                           else f"{r.get('endpoint')}: {r.get('error')}"))
    return rows
