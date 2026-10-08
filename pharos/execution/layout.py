"""Shared paths, worker layouts, and role parsing.

Projects default to ``<repo>/runtime/projects``. Contracts and skills default
to the repository's ``agents/`` tree. Environment overrides are read at call
time. See ``docs/architecture.md`` for the project overview.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


TASK_FILE = "TASK.md"
ROLE_FILE = ".role"
PID_FILE = ".pid"
LOCK_FILE = ".pid.lock"
STOP_FILE = ".stop"
STATUS_FILE = ".status.json"
LOGS_DIR = "logs"
WORKER_REPORT_DIR = "worker_report"
DEADLINE_FILE = ".run_deadline"


def repo_root() -> Path:
    """The repo root that holds the ``agents/`` tree (contracts + skills).

    The package lives at ``<repo>/pharos/execution/layout.py``; the ``agents/``
    tree is its sibling ``<repo>/agents``. Used to locate the main/worker
    contract + skills defaults (all env-overridable)."""
    return Path(__file__).resolve().parents[2]


def child_env() -> dict:
    """Environment for a detached Python child (a worker loop, the monitor, a
    section loop): the repo root first on PYTHONPATH, so the child imports the
    SAME pharos tree as its parent whichever interpreter/venv is in use."""
    env = os.environ.copy()
    prior = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo_root()) + (os.pathsep + prior if prior else "")
    return env


def agents_root() -> Path:
    """Resolve ``PHAROS_AGENTS_ROOT`` or ``<runtime>/projects``.

    Runtime defaults to ``<repo>/runtime`` and can be set with ``PHAROS_RUNTIME``.
    The default is independent of the current working directory.
    """
    env = os.environ.get("PHAROS_AGENTS_ROOT")
    if env:
        return Path(env).resolve()
    runtime = os.environ.get("PHAROS_RUNTIME")
    base = Path(runtime) if runtime else repo_root() / "runtime"
    return (base / "projects").resolve()


def worker_md() -> Path:
    """The worker contract codex auto-reads (symlinked to AGENTS.md). Pinned path
    ``agents/contracts/worker.md``; override with ``PHAROS_WORKER_CONTRACT``."""
    env = os.environ.get("PHAROS_WORKER_CONTRACT")
    if env:
        return Path(env).resolve()
    return repo_root() / "agents" / "contracts" / "worker.md"


def worker_skills_dir() -> Path:
    """The worker skills dir (symlinked to .agents/skills). Pinned path
    ``agents/skills/worker``; override with ``PHAROS_WORKER_SKILLS``."""
    env = os.environ.get("PHAROS_WORKER_SKILLS")
    if env:
        return Path(env).resolve()
    return repo_root() / "agents" / "skills" / "worker"


def main_md() -> Path:
    """The project main-agent contract codex auto-reads (symlinked as the project
    dir's AGENTS.md). Pinned path ``agents/contracts/main_agent.md``.

    The repository's root ``AGENTS.md`` belongs to the deployment operator.
    """
    env = os.environ.get("PHAROS_MAIN_CONTRACT")
    if env:
        return Path(env).resolve()
    return repo_root() / "agents" / "contracts" / "main_agent.md"


def main_skills_dir() -> Path:
    """The project main-agent skills (symlinked to the project's .agents/skills).
    Pinned ``agents/skills/main``.

    The repository's root ``.agents/skills`` belongs to the deployment operator.
    """
    env = os.environ.get("PHAROS_MAIN_SKILLS")
    if env:
        return Path(env).resolve()
    return repo_root() / "agents" / "skills" / "main"


def project_dir(project: str) -> Path:
    return agents_root() / project


def workers_dir(project: str) -> Path:
    return project_dir(project) / "workers"


def worker_dir(project: str, worker: str) -> Path:
    return workers_dir(project) / worker


def list_workers(project: str) -> List[str]:
    wd = workers_dir(project)
    if not wd.is_dir():
        return []
    return sorted(p.name for p in wd.iterdir() if p.is_dir())


def list_projects() -> List[str]:
    """Every project under the agents root (a dir holding a ``workers/`` subdir)."""
    root = agents_root()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "workers").is_dir())


def main_codex_home(project: str) -> Path:
    """The project main agent's CODEX_HOME (its own sessions/history)."""
    return project_dir(project) / ".codex-home"


def materials_dir(project: str) -> Path:
    """Where the operator drops supplied material — papers, references, known
    partial results — that the problem is stated against. Always created, usually
    empty; every agent in the project can read it, but nothing in it is a fact."""
    return project_dir(project) / "materials"


def paper_dir(project: str) -> Path:
    """The writing workspace: OUTLINE.tex, src/ (all tex), verifier/, outputs."""
    return project_dir(project) / "paper"


def paper_src_dir(project: str) -> Path:
    return paper_dir(project) / "src"


STYLE_DIR = "style"
STYLE_TEMPLATE = "TEMPLATE.tex"


def default_style_dir() -> Path:
    """The default style package ``agents/resources/default-style``: STYLE.md,
    TEMPLATE.tex, and the README.md ``pharos new`` copies into a
    project's ``style/``."""
    return repo_root() / "agents" / "resources" / "default-style"


def style_dir(project: str) -> Path:
    """``<project>/style/`` — README.md, ``default`` -> the default package,
    and optionally the operator's own STYLE.md / TEMPLATE.tex / exemplar/.
    Writers read ``style/STYLE.md`` if it exists, else ``style/default/STYLE.md``."""
    return project_dir(project) / STYLE_DIR


def paper_template(project: str) -> Path:
    """The paper template the project compiles through: its own
    ``style/TEMPLATE.tex`` when it provides one, else the default package's.
    Copied once to ``paper/src/template.tex`` (at the first paper verb); the
    main agent edits that copy."""
    own = style_dir(project) / STYLE_TEMPLATE
    return own if own.is_file() else default_style_dir() / STYLE_TEMPLATE


def sections_dir(project: str) -> Path:
    return paper_src_dir(project) / "sections"


def section_dir(project: str, name: str) -> Path:
    """One section's home — its writer's codex cwd: section.tex, TASK.md,
    REPORT.md, and a ``verifier/`` home for that section's stateful verifier."""
    return sections_dir(project) / name


def section_verifier_dir(project: str, name: str) -> Path:
    return section_dir(project, name) / "verifier"


def paper_verifier_dir(project: str) -> Path:
    """The whole-paper verifier's home (stateful across build rounds)."""
    return paper_dir(project) / "verifier"


def stamped_name(project: str) -> str:
    """Output naming for papers and reports: ``<project>_<YYMMDDHHMM>``."""
    import time
    return f"{project}_{time.strftime('%y%m%d%H%M')}"


def contract(name: str) -> Path:
    """``agents/contracts/<name>.md`` (reporter · section_writer · paper_verifier …)."""
    return repo_root() / "agents" / "contracts" / f"{name}.md"


def skills(name: str) -> Path:
    """``agents/skills/<name>`` (reporter · section · paper-verify …)."""
    return repo_root() / "agents" / "skills" / name


def computation_dir(project: str) -> Path:
    """The one place computation scripts AND their outputs live — the cwd of
    every ``pharos compute`` job, size-capped (default 20G). Nothing in it is a
    fact; a proof leaning on a computation still goes through the verifier."""
    return project_dir(project) / "computation"


def routes_md(project: str) -> Path:
    """The route board: the main agent's live strategy record, rewritten in
    place; every checkpoint copies it (the `checkpoint` skill)."""
    return project_dir(project) / "ROUTES.md"


def checkpoints_dir(project: str) -> Path:
    """The main agent's checkpoints, one file each; the latest is the last by
    name (the `checkpoint` skill)."""
    return project_dir(project) / "checkpoints"


def literature_dir(project: str) -> Path:
    """The prior-work survey: SURVEY.md, papers/ (one copy per project, read by
    the main agent's helpers and by workers), notes/ (the `prior-work` skill)."""
    return project_dir(project) / "literature"


def expert_guidance_dir(project: str) -> Path:
    """The expert's standing direction: ``GUIDANCE.md`` (the digest the main
    agent re-reads before every strategy decision), ``INSTRUCTIONS.md`` (the
    verbatim append-only ledger of every instruction). See the
    ``human-interaction`` skill."""
    return project_dir(project) / "expert_guidance"


def subagents_dir(project: str) -> Path:
    """Root for the main agent's helper subagents (``sub1``, ``sub2``, …)."""
    return project_dir(project) / "subagents"


def human_report_dir(project: str) -> Path:
    """Timestamped human reports: ``md/`` and ``pdf/`` pairs, in order."""
    return project_dir(project) / "human_report"


def reporter_dir(project: str) -> Path:
    """The report writer's session home, separate from the main agent's sessions."""
    return project_dir(project) / "reporter"


def chat_dir(project: str) -> Path:
    """Session home for interactive discussions about the project."""
    return project_dir(project) / "chat"


def verifier_dir(project: str) -> Path:
    """This project's verifier home — the codex ``-C`` working directory of every
    cold-start verification, with contract and skills links, sessions, and run logs.
    """
    return project_dir(project) / "verifier"


def verifier_codex_home(project: str) -> Path:
    """The verifier's CODEX_HOME (every cold-start session for this project)."""
    return verifier_dir(project) / ".codex-home"


def verifier_runs_dir(project: str) -> Path:
    """Per-call run dirs (``log.md`` + ``verification.json``), one per check."""
    return verifier_dir(project) / "runs"


def verifier_md() -> Path:
    """The verifier contract (symlinked as the verifier home's AGENTS.md)."""
    env = os.environ.get("PHAROS_VERIFIER_CONTRACT")
    if env:
        return Path(env).resolve()
    return repo_root() / "agents" / "contracts" / "verifier.md"


def verify_skills_dir() -> Path:
    """The verify skills (symlinked as the verifier home's .agents/skills)."""
    env = os.environ.get("PHAROS_VERIFY_SKILLS")
    if env:
        return Path(env).resolve()
    return repo_root() / "agents" / "skills" / "verify"


DEFAULT_VERIFY_PORT_BASE = 8091


@dataclass(frozen=True)
class WorkerLayout:
    """Typed view of one worker home. ``dir`` is that worker's codex cwd;
    every control file is a property so callers never re-spell the names."""

    dir: Path

    @property
    def name(self) -> str:
        return self.dir.name

    @property
    def project_dir(self) -> Path:
        # <project>/workers/<worker>  ->  <project>
        return self.dir.parents[1]

    @property
    def project(self) -> str:
        return self.project_dir.name

    @property
    def task(self) -> Path:
        return self.dir / TASK_FILE

    @property
    def role(self) -> Path:
        return self.dir / ROLE_FILE

    @property
    def pid(self) -> Path:
        return self.dir / PID_FILE

    @property
    def lock(self) -> Path:
        return self.dir / LOCK_FILE

    @property
    def stop(self) -> Path:
        return self.dir / STOP_FILE

    @property
    def status(self) -> Path:
        return self.dir / STATUS_FILE

    @property
    def logs(self) -> Path:
        return self.dir / LOGS_DIR

    @property
    def worker_reports(self) -> Path:
        return self.project_dir / WORKER_REPORT_DIR / self.name

    @property
    def local_memory(self) -> Path:
        return self.dir / "local_memory"

    @property
    def codex_config(self) -> Path:
        return self.dir / ".codex" / "config.toml"

    @property
    def codex_home(self) -> Path:
        """This worker's CODEX_HOME — its own conversation records."""
        return self.dir / ".codex-home"


def resolve_target(target: str) -> Tuple[str, Optional[str]]:
    """``"proj"`` -> (proj, None);  ``"proj/worker"`` -> (proj, worker)."""
    target = target.strip().strip("/")
    if "/" in target:
        project, worker = target.split("/", 1)
        return project, (worker or None)
    return target, None


def target_worker_dirs(target: str) -> List[Path]:
    """Worker dirs addressed by ``target`` — one (proj/worker) or all (proj)."""
    project, worker = resolve_target(target)
    if worker:
        return [worker_dir(project, worker)]
    return [worker_dir(project, w) for w in list_workers(project)]


_ROLE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*?):(\d+)$")


def parse_roles(spec: str) -> List[Tuple[str, str]]:
    """``"xhigh:3,max:4"`` -> ``[("xhigh","xhigh"), ("xhigh2","xhigh"),
    ("xhigh3","xhigh"), ("max","max"), …]``. Returns (worker_name, base_role)
    pairs; the base role (digits stripped) drives the codex reasoning effort. The
    first worker of a base keeps the bare name; the rest get numeric suffixes.
    Raises ``ValueError`` on a malformed/empty spec or a count < 1."""
    out: List[Tuple[str, str]] = []
    for part in (p.strip() for p in spec.split(",") if p.strip()):
        m = _ROLE_RE.match(part)
        if not m:
            raise ValueError(f"bad role spec {part!r}; want e.g. xhigh:3,max:4")
        base, count = m.group(1), int(m.group(2))
        if count < 1:
            raise ValueError(f"role count must be >= 1: {part!r}")
        for i in range(1, count + 1):
            name = base if i == 1 else f"{base}{i}"
            out.append((name, base))
    if not out:
        raise ValueError("empty role spec")
    return out
