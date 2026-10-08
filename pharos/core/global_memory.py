"""Project findings stored in one append-only JSONL file per kind, with BM25 search."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import bm25
from ._util import append_jsonl, read_jsonl, utc_now
from .schema import GLOBAL_KINDS


# path -> (bytes consumed, entries, tokens); per process, discardable.
_TAIL: Dict[Path, tuple] = {}


class GlobalMemory:
    """Rooted at the project directory; shared by all workers + the main agent."""

    def __init__(self, root: Path) -> None:
        self.dir = Path(root) / "global_memory"

    def _path(self, kind: str) -> Path:
        return self.dir / f"{kind}.jsonl"

    def append(
        self,
        kind: str,
        claim: str,
        evidence: str,
        author: str,
        *,
        verifiable: Optional[bool] = None,
        links: Optional[Dict[str, Any]] = None,
        glossary: Optional[Dict[str, str]] = None,
        **extra: Any,
    ) -> str:
        """Publish a finding (claim + evidence). Returns its id.

        ``verifiable`` defaults to the kind's default; objectively-checkable
        kinds require non-empty ``evidence`` (a proof/construction). ``glossary``
        (symbol -> definition) is optional but encouraged: define your symbols
        and reuse the project's terminology, so the finding stays readable and
        carries cleanly into a fact.
        """
        if kind not in GLOBAL_KINDS:
            raise ValueError(f"unknown kind '{kind}'. Known: {sorted(GLOBAL_KINDS)}")
        if verifiable is None:
            verifiable = GLOBAL_KINDS[kind]
        if verifiable and not (evidence or "").strip():
            raise ValueError(f"kind '{kind}' is verifiable and requires explicit evidence")
        ts = utc_now()
        entry_id = hashlib.sha256(
            json.dumps([kind, claim, author, ts], ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
        append_jsonl(
            self._path(kind),
            {
                "id": entry_id,
                "timestamp_utc": ts,
                "author": author,
                "kind": kind,
                "claim": claim,
                "evidence": evidence,
                "verifiable": verifiable,
                "status": "unverified" if verifiable else "open",
                "fact_id": None,
                "links": links or {},
                "glossary": glossary or {},
                **extra,
            },
        )
        return entry_id

    def read(self, kind: str) -> List[Dict[str, Any]]:
        """All entries of a kind."""
        return read_jsonl(self._path(kind))

    def _tail(self, kind: str):
        """(entries, tokens) for one kind, extended from the file's unread tail."""
        path = self._path(kind)
        if not path.exists():
            return [], []
        size = path.stat().st_size
        offset, entries, tokens = _TAIL.get(path, (0, [], []))
        if size < offset:                                  # rewritten: start over
            offset, entries, tokens = 0, [], []
        if size > offset:
            with path.open("rb") as f:
                f.seek(offset)
                chunk = f.read()
            cut = chunk.rfind(b"\n") + 1                 # only complete lines
            for line in chunk[:cut].decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entries.append(entry)
                tokens.append(bm25.tokenize(json.dumps(entry, ensure_ascii=False)))
            _TAIL[path] = (offset + cut, entries, tokens)
        return entries, tokens

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """One entry by id (any kind), from the cached tails."""
        for kind in GLOBAL_KINDS:
            for e in self._tail(kind)[0]:
                if e.get("id") == entry_id:
                    return e
        return None

    def search(
        self, query: str, kinds: Optional[List[str]] = None, limit_per_kind: int = 10
    ) -> Dict[str, Any]:
        """Rank findings from the chosen kinds (default: all) with BM25.

        Parsed entries and tokens are cached; each call reads the appended tail.
        """
        out: Dict[str, Any] = {}
        for kind in (kinds or list(GLOBAL_KINDS)):
            entries, docs = self._tail(kind)
            scores = bm25.bm25_scores(query, docs)
            ranked = []
            for e, s in sorted(zip(entries, scores), key=lambda p: -p[1]):
                if s <= 0:
                    break
                ranked.append({"score": s, "entry": e})
                if len(ranked) >= limit_per_kind:
                    break
            out[kind] = {"count": len(ranked), "results": ranked}
        return {"query": query, "results_by_kind": out}
