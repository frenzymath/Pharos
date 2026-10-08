"""Literature response normalization and HTTP error handling with mocked requests."""

from __future__ import annotations

import io
import json
import urllib.error
from contextlib import contextmanager

from pharos.integrations import matlas


@contextmanager
def _mock_urlopen(payload=None, raise_exc=None):
    orig = matlas.urllib.request.urlopen

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake(req, timeout=None):
        if raise_exc is not None:
            raise raise_exc
        return _Resp(json.dumps(payload).encode("utf-8"))

    matlas.urllib.request.urlopen = fake
    try:
        yield
    finally:
        matlas.urllib.request.urlopen = orig


def test_empty_query_short_circuits():
    out = matlas.search("   ")
    assert out["count"] == 0 and out["results"] == [] and out["error"] == "empty query"


def test_normalization_of_results():
    payload = [
        {"title": "T1", "theorem": "for all n, ...", "arxiv_id": "2601.00001", "theorem_id": "thm1", "extra": "ignored"},
        {"title": "T2", "theorem": "there exists ...", "arxiv_id": "2601.00002", "theorem_id": "lem2"},
        "junk-not-a-dict",
    ]
    with _mock_urlopen(payload=payload):
        out = matlas.search("some statement", num_results=5)
    assert out["count"] == 2  # the non-dict item is dropped
    r = out["results"][0]
    assert set(r) == {"title", "theorem", "arxiv_id", "theorem_id"}
    assert r["arxiv_id"] == "2601.00001" and "error" not in out


def test_network_error_never_raises():
    with _mock_urlopen(raise_exc=urllib.error.URLError("boom")):
        out = matlas.search("x")
    assert out["results"] == [] and out["count"] == 0 and out["error"].startswith("network:")


def test_http_error_yields_error_envelope():
    exc = urllib.error.HTTPError(url=matlas._URL, code=403, msg="Forbidden", hdrs=None, fp=None)
    with _mock_urlopen(raise_exc=exc):
        out = matlas.search("x")
    assert out["results"] == [] and out["count"] == 0
    assert out["error"].startswith("http 403")
