#!/usr/bin/env python3
"""MCP tools for project stores, proof verification, and literature search.

``roles.py`` controls which tools each role may access. ``fact_submit`` writes
facts only after a correct verifier verdict and records verdicts in global memory.

Configuration is read from the environment at call time:
  PHAROS_PROJECT_DIR   the project dir a worker is pinned to (fallback for main)
  PHAROS_AGENTS_ROOT   root holding all projects (<root>/<project>); lets main
                      address any project by name via the ``project`` arg
  PHAROS_AUTHOR        this agent's id, for attribution
  PHAROS_ROLE          worker | main | verifier | reader | all
                      (unset falls back to the read-only verifier set)
  PHAROS_VERIFY_URL    verify-service endpoint for fact_submit
  PHAROS_PROBLEM_ID    problem id stamped on written facts (default: project name)
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from pharos._mcp import FastMCP
from pharos.core import FactGraph, GlobalMemory
from pharos.core.factgraph import parse_frontmatter, section_of, statement_of
from pharos.integrations import search as _arxiv_search

from .roles import tools_for

_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _author() -> str:
    return os.environ.get("PHAROS_AUTHOR", "unknown")


def _role() -> str:
    # Missing roles default to read-only access; the full tool set requires "all".
    return os.environ.get("PHAROS_ROLE", "verifier")


def _project(project: Optional[str] = None) -> Path:
    """Resolve the project dir to operate on.

    ``project`` (the main agent's per-call selector) wins: it names a project
    under ``PHAROS_AGENTS_ROOT`` (``<root>/<project>``), so one session can touch
    several projects. With no ``project`` we fall back to ``PHAROS_PROJECT_DIR``
    (a worker is always pinned this way). The name is validated to a single path
    segment — no ``/`` or ``..`` — so it can never escape the agents root."""
    agents_root = os.environ.get("PHAROS_AGENTS_ROOT", "")
    project_dir = os.environ.get("PHAROS_PROJECT_DIR", "")
    if project:
        if not agents_root:
            raise RuntimeError("PHAROS_AGENTS_ROOT is not set; cannot resolve a project by name")
        if not _PROJECT_NAME_RE.match(project):
            raise RuntimeError(f"invalid project name: {project!r}")
        pdir = Path(agents_root) / project
        if not pdir.is_dir():
            raise RuntimeError(f"no such project: {project!r} (under {agents_root})")
        return pdir
    if not project_dir:
        raise RuntimeError("PHAROS_PROJECT_DIR is not set and no project was given")
    return Path(project_dir)


def _gm(project: Optional[str] = None) -> GlobalMemory:
    return GlobalMemory(_project(project))


def _fg(project: Optional[str] = None) -> FactGraph:
    return FactGraph(_project(project))


def _index_url(project: Optional[str] = None) -> Optional[str]:
    """The project's index service (``pharos.index``), if one is configured.

    For the pinned project ``PHAROS_INDEX_URL`` wins (tests / unusual topologies);
    otherwise — and always for a project addressed by name — the ``index_port``
    of that project's ``project.json``. ``None`` means: search in-process."""
    if not project:
        url = os.environ.get("PHAROS_INDEX_URL", "")
        if url:
            return url
    try:
        meta = json.loads((_project(project) / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, RuntimeError):
        return None
    port = meta.get("index_port")
    return f"http://127.0.0.1:{port}" if isinstance(port, int) else None


def _index_call(project: Optional[str], path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """POST to the shared index, returning None to request local search on failure."""
    url = _index_url(project)
    if not url:
        return None
    try:
        timeout = float(os.environ.get("PHAROS_INDEX_TIMEOUT", "60"))
    except ValueError:
        timeout = 60.0
    req = urllib.request.Request(url.rstrip("/") + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted local URL)
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"pharos gateway: index service {url} unavailable ({exc}); searching in-process",
              file=sys.stderr, flush=True)
        return None
    return body if isinstance(body, dict) else None


def _verify(statement: str, proof: str) -> Dict[str, Any]:
    """POST {statement, proof} to the verify service; return its JSON."""
    verify_url = os.environ.get("PHAROS_VERIFY_URL", "")
    if not verify_url:
        raise RuntimeError("PHAROS_VERIFY_URL is not set (verify service not wired yet)")
    try:
        timeout = int(os.environ.get("PHAROS_VERIFY_TIMEOUT", "90000"))
    except ValueError:
        timeout = 90000
    data = json.dumps({"statement": statement, "proof": proof}).encode("utf-8")
    req = urllib.request.Request(
        verify_url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted local URL)
        return json.loads(resp.read().decode("utf-8"))


def gm_add(
    kind: str,
    claim: str,
    evidence: str = "",
    verifiable: Optional[bool] = None,
    glossary: Optional[Dict[str, str]] = None,
    links: Optional[Dict[str, Any]] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish a finding to shared global memory (claim + evidence). Verifiable
    kinds (conclusion/example/counterexample/proof_attempt) require explicit
    evidence; judgments (plan/direction/obstacle) do
    not. Define your symbols in ``glossary`` and reuse project terminology.

    Main agent: pass ``project`` to target one of several projects by name;
    workers omit it (pinned to their own project)."""
    entry_id = _gm(project).append(
        kind, claim=claim, evidence=evidence, author=_author(),
        verifiable=verifiable, glossary=glossary, links=links,
    )
    return {"id": entry_id, "kind": kind}


_SNIPPET = 300


def gm_search(query: str, kinds: Optional[List[str]] = None, limit: int = 12,
              limit_per_kind: int = 10, project: Optional[str] = None) -> Dict[str, Any]:
    """BM25 over shared global-memory findings. Use to reuse others' results,
    avoid duplicate work, and learn which paths already died. Main agent: pass
    ``project`` to search a specific project; workers omit it.

    Returns the best ``limit`` hits **across all kinds** (default 12), ranked,
    plus ``counts_by_kind`` — how many matched per kind — so you can see where
    to dig: pass ``kinds=[...]`` (and a larger ``limit``) to look at one kind
    closely. **Hits are summaries** — id, kind, author, claim, and the first
    few hundred characters of evidence — so a round of searching does not
    flood your context with whole proofs; ``gm_get(id)`` the few you need."""
    raw = _index_call(project, "/gm_search",
                      {"query": query, "kinds": kinds, "limit_per_kind": limit_per_kind})
    if not raw or "results_by_kind" not in raw:
        raw = _gm(project).search(query, kinds=kinds, limit_per_kind=limit_per_kind)
    hits: List[Dict[str, Any]] = []
    for kind in raw["results_by_kind"].values():
        for hit in kind["results"]:
            e = hit["entry"]
            ev = str(e.get("evidence") or "")
            hits.append({"score": hit["score"], "id": e.get("id"), "kind": e.get("kind"),
                         "author": e.get("author"), "status": e.get("status"),
                         "fact_id": e.get("fact_id"), "claim": e.get("claim"),
                         "evidence": ev[:_SNIPPET] + ("…" if len(ev) > _SNIPPET else "")})
    hits.sort(key=lambda h: -h["score"])
    return {"query": query, "results": hits[:max(0, int(limit))],
            "counts_by_kind": {k: v["count"] for k, v in raw["results_by_kind"].items() if v["count"]}}


def gm_get(entry_id: str, project: Optional[str] = None) -> Dict[str, Any]:
    """The full global-memory entry for one id you found with ``gm_search`` —
    the whole evidence, glossary, links. Fetch only the entries you need;
    never page through memory with it."""
    remote = _index_call(project, "/gm_get", {"entry_id": entry_id})
    e = remote["entry"] if remote and "entry" in remote else _gm(project).get(entry_id)
    return {"entry": e} if e else {"entry": None, "error": f"no entry {entry_id!r}"}


def fact_submit(
    statement: str,
    proof: str,
    predecessors: Optional[List[str]] = None,
    glossary_introduces: Optional[Dict[str, str]] = None,
    intuition: str = "",
    source_id: Optional[str] = None,
    external_refs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """The only way to write a fact. Calls the verifier and writes the node IFF
    accepted. On reject, returns repair hints without creating a fact. Cite the
    returned ``fact_id`` in downstream proofs.

    Once a verdict exists, the verification outcome is **always** recorded to
    global memory (kind ``verification``) — accept, reject, or accept-but-write-
    failed — so a verdict is never stored by nobody (the verifier is stateless;
    this worker tool persists it). ``source_id`` optionally links to the
    global-memory finding being promoted.

    When your proof cites an external (published) result, pass it in
    ``external_refs`` as a structured entry — e.g.
    ``{"key": "HL26", "authors": ["Han", "Liu"], "title": "...",
    "arxiv": "2603.03817", "year": 2026, "cited_for": "Theorem 1.2"}`` (ground it
    with ``search_arxiv_theorems``). This is captured on the fact so the
    literature the proof leans on stays traceable; it is mutable metadata and
    does not affect the ``fact_id``."""
    fg = _fg()
    gm = _gm()
    problem_id = os.environ.get("PHAROS_PROBLEM_ID", Path(_project()).name)

    try:
        result = _verify(statement, proof)
    except Exception as e:
        # Record failed verification attempts as well as completed verdicts.
        gm.append("verification", claim=statement, evidence=f"verify error: {e}",
                  author=_author(), verifiable=False, verdict="error", fact_id=None)
        return {"accepted": False, "verdict": "error", "error": str(e)}
    if not isinstance(result, dict):
        return {"accepted": False, "verdict": "error",
                "error": f"verify service returned a non-dict body ({type(result).__name__})"}
    verdict = result.get("verdict")
    accepted = verdict == "correct"
    run_id = result.get("run_id")
    verify_log = (str(_project() / "verifier" / "runs" / run_id / "log.md")
                  if run_id else None)

    # Preserve the verification trace even when writing the fact fails.
    fact_id = None
    write_error = None
    if accepted:
        try:
            fact_id = fg.add(
                problem_id=problem_id, author=_author(), statement=statement, proof=proof,
                predecessors=predecessors, glossary_introduces=glossary_introduces,
                intuition=intuition, external_refs=external_refs,
            )
        except Exception as e:
            write_error = str(e)

    gm.append(
        "verification",
        claim=statement,
        evidence="verdict: correct" if accepted else (result.get("repair_hints") or "verdict: wrong"),
        author=_author(),
        verifiable=False,
        links={"source_id": source_id, "predecessors": predecessors or []},
        verdict=verdict,
        fact_id=fact_id,
        write_error=write_error,
        verification_report=result.get("verification_report"),
        verify_log=verify_log,
    )

    if not accepted:
        return {
            "accepted": False,
            "verdict": verdict,
            "repair_hints": result.get("repair_hints"),
            "verification_report": result.get("verification_report"),
            "verify_log": verify_log,
        }
    if write_error:
        return {"accepted": True, "fact_id": None, "write_error": write_error,
                "verify_log": verify_log}
    return {"accepted": True, "fact_id": fact_id, "verify_log": verify_log}


# Facts already shown by this gateway session, grouped by project.
_SEEN: Dict[str, set] = {}


def _seen(project: Optional[str]) -> set:
    return _SEEN.setdefault(str(_project(project)), set())


def fact_search(query: str, limit: int = 10, project: Optional[str] = None) -> Dict[str, Any]:
    """BM25 search over the verified fact graph (statement + proof + glossary),
    the derived fact index rebuilt on demand from the fact files — the fact graph
    stays the single source of truth (the index lives in the project's index
    service when one runs, else in this process). Use it **before proving** to check whether a
    fact like yours already exists, and to find the verified facts that bear on
    your subgoal so you can cite their ``fact_id``. Returns ranked ``{fact_id,
    score, statement}``; a fact whose statement you were already shown in this
    session comes back as ``{fact_id, score, seen: true}`` — it is above in your
    context, or one ``fact_get`` away. Main agent: pass ``project`` to search a
    specific project's graph; workers omit it."""
    seen = _seen(project)
    remote = _index_call(project, "/fact_search", {"query": query, "limit": limit})
    hits = remote["results"] if remote and isinstance(remote.get("results"), list) \
        else _fg(project).search(query, limit=limit)
    out = []
    for hit in hits:
        if hit["fact_id"] in seen:
            out.append({"fact_id": hit["fact_id"], "score": hit["score"], "seen": True})
        else:
            seen.add(hit["fact_id"])
            out.append(hit)
    return {"query": query, "results": out}


def fact_get(fact_id: str, with_proof: bool = False, project: Optional[str] = None) -> Dict[str, Any]:
    """One verified fact by id: its statement, predecessors and the symbols it
    introduces; ``with_proof=True`` adds the proof. Citing a fact needs only its
    statement (that is what the verifier reads); fetch the proof when you need
    its technique."""
    raw = _fg(project).get_raw(fact_id)
    if raw is None:
        return {"error": f"unknown fact_id {fact_id!r}"}
    _seen(project).add(fact_id)
    meta = parse_frontmatter(raw)
    out = {"fact_id": fact_id, "statement": section_of(raw, "statement"),
           "predecessors": meta["predecessors"], "glossary_introduces": meta["glossary_introduces"]}
    if with_proof:
        out["proof"] = section_of(raw, "proof")
    return out


def fact_revoke(fact_id: str, reason: str, confirm: bool = False,
                project: Optional[str] = None) -> Dict[str, Any]:
    """Cascade-revoke a wrong fact and everything that depends on it —
    destructive, main-agent only, and **two-step**: without ``confirm`` it only
    lists what would go (each dependent with its statement) so you can see what
    the cascade sweeps; call again with ``confirm=True`` to do it. A dependent
    whose statement is still valuable is re-proved afterwards (assign a worker),
    not spared: as written it stands on a wrong fact."""
    fg = _fg(project)
    if not fg.exists(fact_id):
        return {"error": f"unknown fact_id {fact_id!r}"}
    cascade = [fact_id] + fg.descendants(fact_id)
    if not confirm:
        return {"would_revoke": [{"fact_id": f, "statement": statement_of(fg.get_raw(f) or "")}
                                 for f in cascade],
                "count": len(cascade), "confirm": False}
    return {"revoked": fg.revoke(fact_id, reason=reason)}


def search_arxiv_theorems(query: str, num_results: int = 10) -> Dict[str, Any]:
    """Semantic search over arXiv theorem statements (Matlas). Returns
    **verbatim, as-published** theorem / lemma / definition statements — statement
    fidelity matters for math reasoning and citation checking. Phrase the query as
    a *complete mathematical statement* when possible. Returns ranked results,
    each with ``title``, the full ``theorem`` text, ``arxiv_id``, and the in-paper
    ``theorem_id``. External HTTP, no auth; on outage returns an ``error`` and
    empty ``results`` (retry / fall back to built-in web search)."""
    return _arxiv_search(query, num_results=num_results)


_TOOLS = {
    "gm_add": gm_add,
    "gm_search": gm_search,
    "gm_get": gm_get,
    "fact_submit": fact_submit,
    "fact_search": fact_search,
    "fact_get": fact_get,
    "fact_revoke": fact_revoke,
    "search_arxiv_theorems": search_arxiv_theorems,
}


def build_app(role: Optional[str] = None) -> FastMCP:
    """Build the stdio MCP app exposing exactly the tools ``role`` may use.
    ``role`` defaults to ``PHAROS_ROLE`` (env); unset falls back to the read-only
    verifier set (fail-closed)."""
    app = FastMCP("pharos-core")
    for name in tools_for(role if role is not None else _role()):
        app.tool(name=name)(_TOOLS[name])
    return app
