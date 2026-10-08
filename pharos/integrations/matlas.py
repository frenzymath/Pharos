"""arXiv theorem search (Matlas).

Retrieves theorem, lemma, and definition statements with ``arxiv_id`` and
``theorem_id``. HTTP failures return an error envelope with empty results.

API (no auth):
  POST https://leansearch.net/thm/search  {"query": str, "task": str, "num_results": int}
       -> 200, a JSON **list**; each item normalized to
          {title, theorem, arxiv_id, theorem_id}

Env:
  MATLAS_URL   override the endpoint (default https://leansearch.net/thm/search)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List

_URL = os.environ.get("MATLAS_URL", "https://leansearch.net/thm/search")

# The retrieval task the endpoint conditions on.
_TASK = (
    "Given a math statement, retrieve useful references, such as theorems, "
    "lemmas, and definitions, that are useful for solving the given problem."
)

_DEFAULT_TIMEOUT = 30

# The fields each normalized result carries.
RESULT_FIELDS = ("title", "theorem", "arxiv_id", "theorem_id")


def search(query: str, num_results: int = 10, timeout: int = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Search arXiv theorem statements matching ``query`` (a math statement).

    Returns ``{"query", "count", "results": [{title, theorem, arxiv_id,
    theorem_id}, ...], "endpoint"}``. HTTP and response errors return the same
    envelope with ``error`` set and ``results: []``."""
    q = (query or "").strip()
    if not q:
        return {"query": query, "count": 0, "results": [], "endpoint": _URL, "error": "empty query"}
    n = int(num_results) if num_results and int(num_results) > 0 else 10
    payload = json.dumps({"query": q, "task": _TASK, "num_results": n}).encode("utf-8")
    req = urllib.request.Request(
        _URL, data=payload, method="POST",
        # Identify requests to the service and request JSON responses.
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "pharos/1.0 (+https://frenzymath.com)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted service)
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"query": q, "count": 0, "results": [], "endpoint": _URL, "error": f"http {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"query": q, "count": 0, "results": [], "endpoint": _URL, "error": f"network: {e.reason}"}
    except (TimeoutError, json.JSONDecodeError, ValueError) as e:
        return {"query": q, "count": 0, "results": [], "endpoint": _URL, "error": f"{type(e).__name__}: {e}"}

    if not isinstance(data, list):
        return {"query": q, "count": 0, "results": [], "endpoint": _URL,
                "error": f"theorem endpoint must return a JSON list, got {type(data).__name__}"}

    results: List[Dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        results.append({field: str(item.get(field, "")) for field in RESULT_FIELDS})
    return {"query": q, "count": len(results), "results": results, "endpoint": _URL}
