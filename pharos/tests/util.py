"""Shared test helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager


@contextmanager
def env(**kv):
    """Temporarily set environment variables; ``None`` removes a variable."""
    old = {k: os.environ.get(k) for k in kv}
    for k, v in kv.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = str(v)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def expect_exit(fn, *a, **kw):
    """Call ``fn`` expecting SystemExit; return the exception for its message."""
    try:
        fn(*a, **kw)
    except SystemExit as e:
        return e
    raise AssertionError(f"expected SystemExit from {getattr(fn, '__name__', fn)}")
