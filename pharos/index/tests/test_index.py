"""The index service returns what the in-process index returns, sees new writes,
and the gateway forwards to it — or falls back — without changing results."""

from __future__ import annotations

import json
import tempfile
import threading
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from pharos.core import FactGraph, GlobalMemory
from pharos.gateway import server as gw
from pharos.index import build_server
from pharos.tests.util import env as _env


def _post(url: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(url + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


@contextmanager
def _service(pdir: Path):
    httpd = build_server(pdir, "127.0.0.1", 0)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def _seed(pdir: Path):
    fg = FactGraph(pdir)
    f1 = fg.add(problem_id="p", author="w", statement="Every compact group is unimodular.",
                proof="Haar measure argument.")
    f2 = fg.add(problem_id="p", author="w", statement="The torus is compact.", proof="Product of circles.")
    gm = GlobalMemory(pdir)
    e1 = gm.append("conclusion", claim="unimodular groups have a bi-invariant Haar measure",
                   evidence="see the compact case", author="w")
    return fg, gm, f1, f2, e1


def test_service_matches_in_process_and_sees_new_writes():
    with tempfile.TemporaryDirectory() as d:
        pdir = Path(d) / "proj"
        fg, gm, f1, f2, e1 = _seed(pdir)
        with _service(pdir) as url:
            with urllib.request.urlopen(url + "/health", timeout=5) as resp:
                health = json.loads(resp.read())
            assert health["status"] == "ok" and health["project"] == "proj"

            remote = _post(url, "/fact_search", {"query": "compact", "limit": 5})["results"]
            local = fg.search("compact", limit=5)
            assert remote == local and {h["fact_id"] for h in remote} == {f1, f2}

            remote_gm = _post(url, "/gm_search", {"query": "Haar", "limit_per_kind": 5})
            assert remote_gm == gm.search("Haar", limit_per_kind=5)
            assert remote_gm["results_by_kind"]["conclusion"]["count"] == 1

            assert _post(url, "/gm_get", {"entry_id": e1})["entry"]["id"] == e1
            assert _post(url, "/gm_get", {"entry_id": "nope"})["entry"] is None

            # a write after the service started is visible on the next call
            f3 = fg.add(problem_id="p", author="w", statement="A compact Lie group admits an invariant measure.",
                        proof="Use Haar measure.")
            assert f3 in {h["fact_id"] for h in _post(url, "/fact_search", {"query": "compact Lie"})["results"]}
            e2 = gm.append("obstacle", claim="Haar measure on a noncompact group is infinite",
                           evidence="volume", author="w")
            assert _post(url, "/gm_get", {"entry_id": e2})["entry"]["kind"] == "obstacle"

            # bad input is a clean 4xx, not a dead service
            try:
                _post(url, "/fact_search", [])  # type: ignore[arg-type]
            except urllib.error.HTTPError as exc:
                assert exc.code == 400
            else:
                raise AssertionError("expected 400")
            assert _post(url, "/fact_search", {"query": "compact"})["results"]


def test_gateway_forwards_to_service_and_falls_back():
    with tempfile.TemporaryDirectory() as d:
        pdir = Path(d) / "proj"
        fg, gm, f1, f2, e1 = _seed(pdir)
        with _env(PHAROS_PROJECT_DIR=str(pdir), PHAROS_AGENTS_ROOT=None, PHAROS_INDEX_URL=None):
            direct = gw.fact_search("compact")
            gw_direct = gw.gm_search("Haar")
            gw._SEEN.clear()
        with _service(pdir) as url, _env(PHAROS_PROJECT_DIR=str(pdir), PHAROS_AGENTS_ROOT=None,
                                         PHAROS_INDEX_URL=url):
            assert gw._index_url(None) == url
            assert gw.fact_search("compact") == direct
            assert gw.gm_search("Haar") == gw_direct
            assert gw.gm_get(e1)["entry"]["id"] == e1
            gw._SEEN.clear()
        # service down: the same answers, from the in-process index
        with _env(PHAROS_PROJECT_DIR=str(pdir), PHAROS_AGENTS_ROOT=None,
                  PHAROS_INDEX_URL="http://127.0.0.1:1"):
            assert gw.fact_search("compact") == direct
            assert gw.gm_get(e1)["entry"]["id"] == e1
            gw._SEEN.clear()
        # project.json index_port is honoured for a project addressed by name
        (pdir / "project.json").write_text(json.dumps({"name": "proj", "index_port": 1}), encoding="utf-8")
        with _env(PHAROS_PROJECT_DIR=None, PHAROS_AGENTS_ROOT=d, PHAROS_INDEX_URL=None):
            assert gw._index_url("proj") == "http://127.0.0.1:1"
            assert gw.fact_search("compact", project="proj") == direct   # falls back, port 1 is closed
            gw._SEEN.clear()
