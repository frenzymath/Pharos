"""MCP tool permissions by role.

Workers can submit facts for verification; main agents can revoke them.
Verifiers have literature search only. Readers have read access to shared
stores and literature. The explicit ``all`` role is for development use.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# Names must match the functions registered in server.py.
ALL_TOOLS: Tuple[str, ...] = (
    "gm_add",
    "gm_search",
    "gm_get",
    "fact_submit",
    "fact_search",
    "fact_get",
    "fact_revoke",
    "search_arxiv_theorems",
)

ROLE_TOOLS: Dict[str, Tuple[str, ...]] = {
    "worker": ("gm_add", "gm_search", "gm_get", "fact_submit", "fact_search", "fact_get", "search_arxiv_theorems"),
    "main": ("gm_add", "gm_search", "gm_get", "fact_search", "fact_get", "fact_revoke", "search_arxiv_theorems"),
    "verifier": ("search_arxiv_theorems",),
    "reader": ("gm_search", "gm_get", "fact_search", "fact_get", "search_arxiv_theorems"),
    "all": ALL_TOOLS,
}


def tools_for(role: str) -> List[str]:
    """Return allowed tools, defaulting unknown roles to the read-only verifier set."""
    return list(ROLE_TOOLS.get(role, ROLE_TOOLS["verifier"]))
