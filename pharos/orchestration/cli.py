"""Parse commands, enforce directory scope, and format results for ``pharos``.

Command implementations live in the adjacent orchestration modules; project
layout and provisioning live in ``pharos.execution``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from pharos.execution import layout as L
from pharos.execution.scaffold import do_new
from .workers import (do_assign, do_list, do_start, do_status, do_stop,
                      worker_status)

__all__ = [
    "do_new", "do_assign", "do_start", "do_status", "worker_status",
    "do_list", "do_stop", "build_parser", "main",
]


def _fmt_list(rows: List[Dict]) -> str:
    head = f"{'PROJECT':<24}{'WORKERS':>8}{'LIVE':>6}  {'MODEL':<12}"
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(f"{r['project']:<24}{r['workers']:>8}{r['live']:>6}  {str(r['model']):<12}")
    return "\n".join(lines) if rows else "(no projects under the agents root)"


def _fmt_status(rows: List[Dict]) -> str:
    head = (f"{'WORKER':<14}{'LABEL':<12}{'STATE':<13}{'ROUND':>6}  {'AGE':>7}  "
            f"{'ACTIVE':>8}  {'LAST_FACT':<16}")
    lines = [head, "-" * len(head)]
    for r in rows:
        age = f"{r['age_s']:.0f}s" if r["age_s"] is not None else "—"
        active = f"{r['silent_s']:.0f}s ago" if r.get("silent_s") is not None else "—"
        lines.append(f"{r['worker']:<14}{r['label']:<12}{r['state']:<13}"
                     f"{r['round']:>6}  {age:>7}  {active:>8}  {str(r['last_fact_id'] or '—'):<16}")
    return "\n".join(lines)


def _task_from_args(args) -> str:
    import sys
    if args.task is not None:
        return args.task
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.stdin:
        return sys.stdin.read()
    raise SystemExit("assign needs one of --task, --file, or --stdin")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pharos",
        description="Run Pharos. What you may do here depends on the directory you "
                    "are in: the repo root is the ops agent's (every verb, any "
                    "project named explicitly); a project directory is that "
                    "project's main agent's (its own verbs, project implicit).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    li = sub.add_parser("list", help="all projects + live worker counts")
    li.add_argument("--json", action="store_true")

    n = sub.add_parser("new", help="scaffold a project (workers, main-agent session, verify port)")
    n.add_argument("project")
    n.add_argument("--roles", default="xhigh:3,max:4", help="e.g. xhigh:3,max:4 (default)")
    n.add_argument("--model", default=None)
    n.add_argument("--port", type=int, default=None,
                   help="the verify port (default: the lowest free one at/above VERIFY_PORT)")

    m = sub.add_parser("main", help="a project's resident main agent (tmux)")
    m_sub = m.add_subparsers(dest="action", required=True)
    m_start = m_sub.add_parser("start", help="start it detached in tmux")
    m_start.add_argument("project")
    m_start.add_argument("--tag", default=None,
                         help="3–4 char abbreviation of the experiment; the tmux "
                              "session is pharos-v3-<tag> (proof-demo -> demo). "
                              "Recorded in project.json on first use.")
    m_status = m_sub.add_parser("status", help="which projects have a live main agent")
    m_status.add_argument("project", nargs="?")

    doc = sub.add_parser("doctor", help="health of the whole stack; --probe also renders a PDF, "
                                        "compiles the paper template and queries the literature service")
    doc.add_argument("--probe", action="store_true",
                     help="exercise render, TeX and matlas for real; essentials become FAIL")
    doc.add_argument("--json", action="store_true")

    a = sub.add_parser("assign", help="write a worker's per-round TASK.md")
    a.add_argument("target", nargs="?", help="<worker> here, <project>/<worker> from the root")
    a.add_argument("--task", default=None)
    a.add_argument("--file", default=None)
    a.add_argument("--stdin", action="store_true")

    s = sub.add_parser("start", help="launch worker loop(s)")
    s.add_argument("target", nargs="?")

    st = sub.add_parser("status", help="worker liveness + progress")
    st.add_argument("target", nargs="?")
    st.add_argument("--json", action="store_true")

    sp = sub.add_parser("stop", help="stop worker loop(s)")
    sp.add_argument("target", nargs="?")
    sp.add_argument("--force", action="store_true", help="kill now (else finish current round)")

    sa = sub.add_parser("sub", help="run a main-agent helper subagent in subagents/subN")
    sa.add_argument("target", nargs="?", help="<project> or <project>/subN (subN reuses that home)")
    sa.add_argument("prompt", nargs="*", help="the question for the helper")

    v = sub.add_parser("verify", help="this project's verify service")
    v_sub = v.add_subparsers(dest="action", required=True)
    for action, helptext in (("up", "start it"), ("down", "stop it"),
                             ("status", "is it up, and is it ours?")):
        vp = v_sub.add_parser(action, help=helptext)
        vp.add_argument("project", nargs="?")
    vport = v_sub.add_parser("port", help="move the project to another verify port "
                                          "(service down first): [<project>] <port>")
    vport.add_argument("args", nargs="+", metavar="[<project>] <port>")

    ix = sub.add_parser("index", help="the project's index service: one copy of the search caches "
                                      "instead of one per codex session")
    ix_sub = ix.add_subparsers(dest="action", required=True)
    for action, helptext in (("up", "start it (allocates index_port on first use)"), ("down", "stop it"),
                             ("status", "is it up, and is it ours?")):
        ip = ix_sub.add_parser(action, help=helptext)
        ip.add_argument("project", nargs="?")

    mo = sub.add_parser("monitor", help="the project's liveness/load sampler (monitor.jsonl)")
    mo_sub = mo.add_subparsers(dest="action", required=True)
    for action, helptext in (("up", "start sampling"), ("down", "stop it"),
                             ("status", "is it sampling?")):
        mp = mo_sub.add_parser(action, help=helptext)
        mp.add_argument("project", nargs="?")

    us = sub.add_parser("usage", help="tokens/cost, elapsed time, liveness history")
    us.add_argument("project", nargs="?")
    us.add_argument("--json", action="store_true")

    rd = sub.add_parser("render", help="markdown (TeX math ok) -> paper-like PDF")
    rd.add_argument("markdown", help="the .md file (human_report/md/<ts>.md by convention)")
    rd.add_argument("-o", "--out", default=None,
                    help="output PDF (default: sibling pdf/ dir, else alongside)")

    ch = sub.add_parser(
        "chat", help="open an interactive discussion session about the project "
                     "(records land in <project>/chat/, never the main agent's)")
    ch.add_argument("project", nargs="?")

    rp = sub.add_parser("report", help="write a human report now (a fresh reporter session)")
    rp.add_argument("project", nargs="?")

    pp = sub.add_parser("paper", help="the writing workspace: section writers, verifiers, build")
    pp.add_argument("--project", default=None, help="(ops only) the project; implicit in a project dir")
    pa = pp.add_subparsers(dest="action", required=True)
    a_ = pa.add_parser("assign", help="write a section's TASK.md (provisions the section home)")
    a_.add_argument("section")
    a_.add_argument("--task", default=None)
    a_.add_argument("--file", default=None)
    a_.add_argument("--stdin", action="store_true")
    s_ = pa.add_parser("start", help="run a section writer (detached; resumes its own session)")
    s_.add_argument("section", nargs="?")
    s_.add_argument("--all", action="store_true")
    pa.add_parser("status", help="every section: state · rounds · last change")
    w_ = pa.add_parser("wait", help="block until a section reports (any, or the named ones)")
    w_.add_argument("sections", nargs="*")
    w_.add_argument("--timeout", type=int, default=0, help="seconds; 0 = no limit")
    st_ = pa.add_parser("stop", help="stop a running section writer")
    st_.add_argument("section")
    pa.add_parser("build", help="assemble src/main.tex from the template + sections, compile")
    v_ = pa.add_parser("verify", help="run a section's stateful verifier, or the whole-paper one")
    v_.add_argument("section", nargs="?")
    v_.add_argument("--global", dest="whole", action="store_true")

    co = sub.add_parser(
        "compute", help="run a computation script under the enforced caps "
                        "(cgroup slice: 4 CPUs / 16G for ALL computation)")
    co.add_argument("script", help="must live in <project>/computation/")
    co.add_argument("--heavy", action="store_true",
                    help="justified need only: per-job cap rises to the pool itself")
    co.add_argument("args", nargs=argparse.REMAINDER,
                    help="passed to the script verbatim")

    cc = sub.add_parser("check-codex", help="is the model backend answering? (+ recent API errors)")
    cc.add_argument("--json", action="store_true")

    mc = sub.add_parser("mcp-call", help="call one MCP tool in a fresh session (pipe recovery)")
    mc.add_argument("tool")
    mc.add_argument("--json", dest="json_args", default=None, help="arguments as one JSON object")
    mc.add_argument("--stdin", action="store_true", help="read the JSON argument object from stdin")
    return p


def _project_meta(project: str) -> Dict:
    """A project's project.json (roster, model, verify_port)."""
    path = L.project_dir(project) / "project.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        raise SystemExit(f"no such project: {project}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}")


def _fmt_doctor(rows: List[Dict]) -> str:
    colour = {"ok": "\033[32mok\033[0m  ", "warn": "\033[33mwarn\033[0m", "FAIL": "\033[31mFAIL\033[0m"}
    return "\n".join(f"  {colour[r['state']]} {r['label']}"
                      + (f" — {r['detail']}" if r["detail"] else "") for r in rows)


def _load_pharos_env() -> None:
    """Load unset variables from ``config/pharos.env`` for direct CLI invocation."""
    cfg = L.repo_root() / "config" / "pharos.env"
    try:
        lines = cfg.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val


def main(argv: Optional[List[str]] = None) -> int:
    from . import scope as _scope
    from . import health, services, subagent

    _load_pharos_env()
    args = build_parser().parse_args(argv)
    # The directory decides what this session may do (see scope.py).
    sc, sc_project = _scope.check(args.cmd)

    if args.cmd == "list":
        rows = do_list()
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else _fmt_list(rows))

    elif args.cmd == "new":
        r = do_new(args.project, roles=args.roles, model=args.model, port=args.port)
        print(f"created {args.project} with {len(r['workers'])} workers: "
              f"{', '.join(r['workers'])}\n  {r['project_dir']}\n"
              f"  verify port {r['verify_port']}\n"
              f"  next: pharos verify up {args.project} && pharos main start {args.project}")

    elif args.cmd == "main":
        if args.action == "start":
            r = services.main_start(args.project, tag=args.tag)
            print(f"{r['session']}: {r['result']}\n  {r['attach']}")
        else:
            projects = [args.project] if args.project else L.list_projects()
            for row in services.main_status(projects):
                print(f"  {'up  ' if row['running'] else 'down'} {row['session']}")

    elif args.cmd == "doctor":
        rows = health.doctor(probe=args.probe)
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json
              else "== Pharos doctor ==\n" + _fmt_doctor(rows))
        return 1 if any(r["state"] == "FAIL" for r in rows) else 0

    elif args.cmd == "check-codex":
        r = health.check_codex()
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        elif r.get("ok"):
            print(f"ok   backend answered ({r.get('latency_s', '?')}s)")
            if r.get("recent_logs_with_api_errors"):
                print(f"warn {r['recent_logs_with_api_errors']} recent log(s) show API errors")
        else:
            print(f"FAIL backend did not answer: {r.get('err') or r.get('detail')}")
        return 0 if r.get("ok") else 1

    elif args.cmd == "assign":
        target = _scope.pin(args.target, sc, sc_project, verb="assign", need_worker=True)
        r = do_assign(target, _task_from_args(args))
        print(f"assigned {r['worker']} -> {r['task_file']}")

    elif args.cmd == "start":
        for r in do_start(_scope.pin(args.target, sc, sc_project, verb="start")):
            print(f"{r['worker']}: {r['result']}")

    elif args.cmd == "status":
        rows = do_status(_scope.pin(args.target, sc, sc_project, verb="status"))
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else _fmt_status(rows))

    elif args.cmd == "stop":
        for r in do_stop(_scope.pin(args.target, sc, sc_project, verb="stop"), force=args.force):
            print(f"{r['worker']}: {r['result']}")

    elif args.cmd == "sub":
        target = _scope.pin(args.target, sc, sc_project, verb="sub")
        return subagent.run(target, " ".join(args.prompt))

    elif args.cmd == "verify":
        if args.action == "port":
            if len(args.args) == 1:
                target, port_s = None, args.args[0]
            elif len(args.args) == 2:
                target, port_s = args.args
            else:
                raise SystemExit("usage: pharos verify port [<project>] <port>")
            if not port_s.isdigit():
                raise SystemExit(f"not a port number: {port_s}")
            project = _scope.pin(target, sc, sc_project, verb="verify")
            r = services.verify_set_port(project, int(port_s))
            print(f"verify-{project}: port {r['old_port']} → {r['verify_port']} "
                  f"(workers pick it up at their next start; now `pharos verify up {project}`)")
            return 0
        project = _scope.pin(args.project, sc, sc_project, verb="verify")
        if args.action == "up":
            r = services.verify_up(project)
            print(f"{r['service']}: {r['result']}")
        elif args.action == "down":
            r = services.verify_down(project)
            print(f"{r['service']}: {r['result']}")
        else:
            for row in services.verify_status([project] if project else L.list_projects()):
                print(f"  {row['state']:<8} verify-{row['project']} :{row.get('port', '?')}")

    elif args.cmd == "index":
        project = _scope.pin(args.project, sc, sc_project, verb="index")
        if args.action == "up":
            r = services.index_up(project)
            print(f"{r['service']}: {r['result']}" + (f" (port {r['port']})" if r.get("port") else ""))
        elif args.action == "down":
            r = services.index_down(project)
            print(f"{r['service']}: {r['result']}")
        else:
            for row in services.index_status([project] if project else L.list_projects()):
                print(f"  {row['state']:<12} index-{row['project']} :{row.get('port') or '-'}")

    elif args.cmd == "monitor":
        project = _scope.pin(args.project, sc, sc_project, verb="monitor")
        if args.action == "up":
            r = services.monitor_up(project)
            print(f"{r['service']}: {r['result']}")
        elif args.action == "down":
            r = services.monitor_down(project)
            print(f"{r['service']}: {r['result']}")
        else:
            for row in services.monitor_status([project] if project else L.list_projects()):
                print(f"  {row['state']:<5} monitor-{row['project']}")

    elif args.cmd == "usage":
        from .usage import format_usage, project_usage
        project = _scope.pin(args.project, sc, sc_project, verb="usage")
        u = project_usage(project)
        print(json.dumps(u, ensure_ascii=False, indent=2) if args.json else format_usage(u))

    elif args.cmd == "render":
        from .render import render
        out = render(Path(args.markdown), Path(args.out) if args.out else None)
        print(f"rendered {out}")

    elif args.cmd == "compute":
        from .compute import run as compute_run
        return compute_run(args.script, args.args, heavy=args.heavy)

    elif args.cmd == "report":
        from .report import run as report_run
        return report_run(_scope.pin(args.project, sc, sc_project, verb="report"))

    elif args.cmd == "paper":
        from .paper import dispatch as paper_dispatch
        return paper_dispatch(_scope.pin(args.project, sc, sc_project, verb="paper"), args)

    elif args.cmd == "chat":
        # The local .codex-home keeps discussion sessions separate from research.
        from pharos import codex as _codex
        from pharos.execution.scaffold import ensure_chat_home
        project = _scope.pin(args.project, sc, sc_project, verb="chat")
        cdir = ensure_chat_home(project)
        os.chdir(cdir)
        cbin = _codex.resolve_bin()
        os.execvp(cbin, [cbin, "--dangerously-bypass-approvals-and-sandbox"])

    elif args.cmd == "mcp-call":
        from .mcp_call import run as mcp_run
        return mcp_run(args.tool, args.json_args, args.stdin)

    return 0
