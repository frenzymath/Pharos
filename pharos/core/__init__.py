"""Project stores, content addressing, and BM25 ranking.

``FactGraph`` holds verifier-accepted facts; ``GlobalMemory`` holds shared
findings that have not necessarily been verified.
"""

from __future__ import annotations

from . import bm25
from .factgraph import FactGraph, parse_frontmatter, serialize_fact, statement_of
from .global_memory import GlobalMemory
from .schema import (
    EXTERNAL_REF_KEYS,
    GLOBAL_KINDS,
    Fact,
    clean_external_refs,
    compute_fact_id,
)

__all__ = [
    "FactGraph",
    "GlobalMemory",
    "Fact",
    "GLOBAL_KINDS",
    "EXTERNAL_REF_KEYS",
    "clean_external_refs",
    "compute_fact_id",
    "serialize_fact",
    "parse_frontmatter",
    "statement_of",
    "bm25",
]
