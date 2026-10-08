"""External literature search services used by the gateway."""

from __future__ import annotations

from .matlas import RESULT_FIELDS, search

__all__ = ["search", "RESULT_FIELDS"]
