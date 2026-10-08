"""Project orchestration and the ``pharos`` command-line interface."""

from __future__ import annotations

from .cli import (
    build_parser,
    do_assign,
    do_list,
    do_new,
    do_start,
    do_status,
    do_stop,
    main,
    worker_status,
)

__all__ = [
    "do_new",
    "do_assign",
    "do_start",
    "do_status",
    "worker_status",
    "do_list",
    "do_stop",
    "build_parser",
    "main",
]
