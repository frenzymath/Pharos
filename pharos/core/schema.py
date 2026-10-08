"""Fact schema, global-memory kinds, and content-addressed fact IDs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List


# kind -> default `verifiable` (objectively checkable vs. a judgment).
GLOBAL_KINDS: Dict[str, bool] = {
    "conclusion": True,
    "example": True,
    "counterexample": True,
    "proof_attempt": True,
    "plan": False,
    "dead_end": False,
    "direction": False,
    "obstacle": False,
    "verification": False,     # trace of a fact_submit verification outcome (logged by fact_submit)
}


# Canonical bibliography key order; additional keys follow in sorted order.
EXTERNAL_REF_KEYS = ("key", "authors", "title", "arxiv", "year", "venue", "doi", "cited_for")


def clean_external_refs(refs: object) -> List[Dict[str, object]]:
    """Normalize reference dictionaries to a stable key order, skipping other entries."""
    if not refs:
        return []
    out: List[Dict[str, object]] = []
    for r in refs:  # type: ignore[union-attr]
        if not isinstance(r, dict):
            continue
        ordered = {k: r[k] for k in EXTERNAL_REF_KEYS if k in r}
        for k in sorted(r):  # preserve any extra keys, deterministically
            if k not in ordered:
                ordered[k] = r[k]
        out.append(ordered)
    return out


@dataclass
class Fact:
    """A verified fact = one node in the fact graph. Frontmatter (fact_id /
    problem_id / author / predecessors / glossary_introduces / external_refs) +
    the markdown body (statement / proof / optional intuition)."""

    fact_id: str
    problem_id: str
    author: str
    predecessors: List[str]                    # bare-hex fact ids (the DAG)
    statement: str
    proof: str
    glossary_introduces: Dict[str, str] = field(default_factory=dict)  # symbol -> definition
    intuition: str = ""
    # Bibliography can be corrected without changing the fact ID or its dependents.
    external_refs: List[Dict[str, object]] = field(default_factory=list)


def _normalize(text: str) -> str:
    """Whitespace-stable canonical form for content hashing (cosmetic edits do
    not perturb the fact_id)."""
    return re.sub(r"\s+", " ", text or "").strip()


def compute_fact_id(
    *,
    problem_id: str,
    predecessors: List[str],
    glossary_introduces: Dict[str, str],
    statement: str,
    proof: str,
) -> str:
    """Return the first 16 hex digits of the canonical content's SHA-256 hash.

    Mutable ``external_refs`` are excluded so bibliography corrections preserve
    graph links. Citation keys within ``proof`` are part of the hash.
    """
    body = {
        "problem_id": problem_id,
        "predecessors": sorted(predecessors),
        "glossary_introduces": dict(
            sorted((str(k), str(v)) for k, v in glossary_introduces.items())
        ),
        "statement": _normalize(statement),
        "proof": _normalize(proof),
    }
    canon = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canon).hexdigest()[:16]
