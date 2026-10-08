"""Content-addressed fact DAG, project glossary, and revocation archive.

Each fact is a Markdown file with frontmatter and statement/proof sections.
The gateway verifies submissions before calling ``add``. This module handles
storage, search, and graph dependencies.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from . import bm25
from ._util import append_jsonl, utc_now
from .schema import Fact, clean_external_refs, compute_fact_id

_PRED_RE = re.compile(r"^predecessors:\s*\[(.*)\]\s*$")
_GLOSS_LINE_RE = re.compile(r"^\s{2}([^:]+):\s*(.*)$")


def section_of(text: str, name: str) -> str:
    """Extract a fact field, preserving headings other than schema delimiters."""
    out: List[str] = []
    inside = False
    for line in text.splitlines():
        if line.strip().lower() in {"## statement", "## proof", "## intuition"}:
            if inside:
                break
            inside = line.strip().lower() == f"## {name}"
            continue
        if inside:
            out.append(line)
    return "\n".join(out).strip()


def statement_of(text: str) -> str:
    """Return the statement as a one-line search snippet."""
    return " ".join(s.strip() for s in section_of(text, "statement").splitlines() if s.strip())


def serialize_fact(fact: Fact) -> str:
    """Render a Fact to its readable markdown-with-frontmatter form."""
    lines = [
        "---",
        f"fact_id: {fact.fact_id}",
        f"problem_id: {fact.problem_id}",
        f"author: {fact.author}",
        f"predecessors: [{', '.join(fact.predecessors)}]",
    ]
    if fact.glossary_introduces:
        lines.append("glossary_introduces:")
        for k in sorted(fact.glossary_introduces):
            lines.append(f"  {k}: {fact.glossary_introduces[k]}")
    else:
        lines.append("glossary_introduces: {}")
    # A JSON array is valid YAML and keeps bibliography parsing self-contained.
    lines.append("external_refs: " + json.dumps(fact.external_refs, ensure_ascii=False))
    lines += ["---", "", "## statement", fact.statement.strip(),
              "", "## proof", fact.proof.strip()]
    if fact.intuition.strip():
        lines += ["", "## intuition", fact.intuition.strip()]
    lines.append("")
    return "\n".join(lines)


def parse_frontmatter(text: str) -> Dict[str, object]:
    """Extract predecessors, glossary, and bibliography from a fact's frontmatter.

    Absent fields default to empty lists or dictionaries.
    """
    preds: List[str] = []
    gloss: Dict[str, str] = {}
    refs: List[Dict[str, object]] = []
    in_gloss = False
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if i > 0 and line.strip() == "---":
            break
        m = _PRED_RE.match(line.strip())
        if m:
            preds = [x.strip() for x in m.group(1).split(",") if x.strip()]
            in_gloss = False
            continue
        if line.strip().startswith("glossary_introduces:"):
            in_gloss = "{}" not in line
            continue
        if line.strip().startswith("external_refs:"):
            in_gloss = False
            payload = line.strip()[len("external_refs:"):].strip()
            try:
                refs = json.loads(payload) if payload else []
            except json.JSONDecodeError:
                refs = []
            continue
        if in_gloss:
            gm = _GLOSS_LINE_RE.match(line)
            if gm:
                gloss[gm.group(1).strip()] = gm.group(2).strip()
            else:
                in_gloss = False
    return {"predecessors": preds, "glossary_introduces": gloss, "external_refs": refs}


# facts_dir -> {fact_id: (mtime_ns, size, tokens, statement)}; per process,
# discardable — the files remain the only truth.
_INDEX: Dict[Path, Dict[str, tuple]] = {}


class FactGraph:
    """Rooted at the project directory; the only correctness source."""

    def __init__(self, root: Path) -> None:
        self.dir = Path(root) / "fact_graph"
        self.facts_dir = self.dir / "facts"
        self.revoked_dir = self.dir / "_revoked"
        self.glossary_path = self.dir / "glossary.json"
        self.revocation_log = self.dir / "revocation_log.jsonl"

    def _path(self, fact_id: str) -> Path:
        return self.facts_dir / f"{fact_id}.md"

    def add(
        self,
        *,
        problem_id: str,
        author: str,
        statement: str,
        proof: str,
        predecessors: Optional[List[str]] = None,
        glossary_introduces: Optional[Dict[str, str]] = None,
        intuition: str = "",
        external_refs: Optional[List[Dict[str, object]]] = None,
    ) -> str:
        """Write a verified fact; return its content-addressed fact_id.

        Refuses a revoked predecessor (cascade integrity). Idempotent: identical
        content -> identical id -> identical file. Merges the fact's introduced
        symbols into the project glossary. ``external_refs`` is structured
        bibliography for cited external results; it does not affect the fact_id.
        """
        predecessors = [p for p in (predecessors or []) if p]
        glossary_introduces = glossary_introduces or {}
        external_refs = clean_external_refs(external_refs)
        for pid in predecessors:
            if (self.revoked_dir / f"{pid}.md").exists():
                raise ValueError(f"predecessor_revoked: {pid}")
        fact_id = compute_fact_id(
            problem_id=problem_id,
            predecessors=predecessors,
            glossary_introduces=glossary_introduces,
            statement=statement,
            proof=proof,
        )
        fact = Fact(
            fact_id=fact_id, problem_id=problem_id, author=author,
            predecessors=predecessors, statement=statement, proof=proof,
            glossary_introduces=glossary_introduces, intuition=intuition,
            external_refs=external_refs,
        )
        self.facts_dir.mkdir(parents=True, exist_ok=True)
        self._path(fact_id).write_text(serialize_fact(fact), encoding="utf-8")
        self._merge_glossary(glossary_introduces)
        return fact_id

    def _merge_glossary(self, new: Dict[str, str]) -> None:
        if not new:
            return
        cur = self.glossary()
        cur.update({str(k): str(v) for k, v in new.items()})
        self.glossary_path.parent.mkdir(parents=True, exist_ok=True)
        self.glossary_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")

    def exists(self, fact_id: str) -> bool:
        return self._path(fact_id).exists()

    def list(self) -> List[str]:
        if not self.facts_dir.exists():
            return []
        return sorted(p.stem for p in self.facts_dir.glob("*.md"))

    def get_raw(self, fact_id: str) -> Optional[str]:
        """The fact's markdown (agents read markdown directly)."""
        p = self._path(fact_id)
        return p.read_text(encoding="utf-8") if p.exists() else None

    def glossary(self) -> Dict[str, str]:
        """The accumulated project glossary (symbol -> definition)."""
        if self.glossary_path.exists():
            try:
                return json.loads(self.glossary_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def search(self, query: str, limit: int = 10) -> List[Dict[str, object]]:
        """Rank fact files with BM25, returning ``{fact_id, score, statement}``.

        The process-local cache tracks file timestamps and sizes, reading only
        new or changed files. Fact files remain the source of truth.
        """
        fids = self.list()
        if not fids:
            return []
        idx = _INDEX.setdefault(self.facts_dir, {})
        for gone in set(idx) - set(fids):
            del idx[gone]
        for fid in fids:
            st = self._path(fid).stat()
            key = (st.st_mtime_ns, st.st_size)
            if fid not in idx or idx[fid][:2] != key:
                raw = self.get_raw(fid) or ""
                idx[fid] = (*key, bm25.tokenize(raw), statement_of(raw))
        scores = bm25.bm25_scores(query, [idx[f][2] for f in fids])
        ranked: List[Dict[str, object]] = []
        for fid, score in sorted(zip(fids, scores), key=lambda t: -t[1]):
            if score <= 0:
                break
            ranked.append({"fact_id": fid, "score": score, "statement": idx[fid][3]})
            if len(ranked) >= limit:
                break
        return ranked

    def predecessors(self, fact_id: str) -> List[str]:
        raw = self.get_raw(fact_id) or ""
        return parse_frontmatter(raw)["predecessors"]  # type: ignore[return-value]

    def external_refs(self, fact_id: str) -> List[Dict[str, object]]:
        """The fact's structured external bibliography (``[]`` if none / absent)."""
        raw = self.get_raw(fact_id) or ""
        return parse_frontmatter(raw)["external_refs"]  # type: ignore[return-value]

    def set_external_refs(self, fact_id: str, external_refs: List[Dict[str, object]]) -> List[Dict[str, object]]:
        """Replace a fact's ``external_refs`` in place — the reference auditor's
        write path. Touches only this mutable frontmatter line; the body and the
        content-addressed ``fact_id`` are unchanged (refs are not hashed). Returns
        the normalized refs written. Raises if the fact does not exist."""
        p = self._path(fact_id)
        if not p.exists():
            raise ValueError(f"unknown fact_id: {fact_id}")
        refs = clean_external_refs(external_refs)
        new_line = "external_refs: " + json.dumps(refs, ensure_ascii=False)
        lines = p.read_text(encoding="utf-8").splitlines()
        # frontmatter is between the first '---' (line 0) and the next '---'
        close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if close is None:
            raise ValueError(f"malformed fact file (no frontmatter close): {fact_id}")
        idx = next((i for i in range(1, close) if lines[i].startswith("external_refs:")), None)
        if idx is not None:
            lines[idx] = new_line
        else:
            lines.insert(close, new_line)
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return refs

    def descendants(self, fact_id: str) -> List[str]:
        """All facts that (transitively) depend on ``fact_id``."""
        out: List[str] = []
        seen = set()
        frontier = [fact_id]
        while frontier:
            cur = frontier.pop()
            for fid in self.list():
                if fid in seen:
                    continue
                if cur in self.predecessors(fid):
                    out.append(fid)
                    seen.add(fid)
                    frontier.append(fid)
        return out

    def revoke(self, fact_id: str, reason: str) -> List[str]:
        """Cascade-revoke ``fact_id`` and everything depending on it. Moves the
        files into ``_revoked/`` and logs each. Returns the revoked ids."""
        if not self.exists(fact_id):
            raise ValueError(f"unknown fact_id: {fact_id}")
        to_revoke = [fact_id] + self.descendants(fact_id)
        self.revoked_dir.mkdir(parents=True, exist_ok=True)
        for fid in to_revoke:
            src = self._path(fid)
            if src.exists():
                shutil.move(str(src), str(self.revoked_dir / f"{fid}.md"))
            append_jsonl(
                self.revocation_log,
                {
                    "timestamp_utc": utc_now(),
                    "fact_id": fid,
                    "reason": reason,
                    "revoked_as_dependent_of": fid != fact_id and fact_id or None,
                },
            )
        return to_revoke
