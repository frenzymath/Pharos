"""Worker loops, project scaffolding, and shared runtime paths."""

from __future__ import annotations

from . import layout
from .layout import (
    DEADLINE_FILE,
    LOCK_FILE,
    LOGS_DIR,
    PID_FILE,
    ROLE_FILE,
    STATUS_FILE,
    STOP_FILE,
    TASK_FILE,
    WorkerLayout,
    agents_root,
    list_projects,
    list_workers,
    parse_roles,
    project_dir,
    repo_root,
    resolve_target,
    target_worker_dirs,
    worker_dir,
    main_md,
    main_skills_dir,
    worker_md,
    worker_skills_dir,
    workers_dir,
)
from .loop import kickoff, main, run_round, write_status
from .scaffold import atomic_write, do_new, spawn_loop, symlink

__all__ = [
    # layout module + API
    "layout",
    "WorkerLayout",
    "agents_root",
    "repo_root",
    "project_dir",
    "workers_dir",
    "worker_dir",
    "list_workers",
    "list_projects",
    "main_md",
    "main_skills_dir",
    "worker_md",
    "worker_skills_dir",
    "resolve_target",
    "target_worker_dirs",
    "parse_roles",
    # control-file name constants
    "TASK_FILE",
    "ROLE_FILE",
    "PID_FILE",
    "LOCK_FILE",
    "STOP_FILE",
    "STATUS_FILE",
    "LOGS_DIR",
    "DEADLINE_FILE",
    # loop
    "main",
    "run_round",
    "write_status",
    "kickoff",
    # scaffolding
    "do_new",
    "spawn_loop",
    "atomic_write",
    "symlink",
]
