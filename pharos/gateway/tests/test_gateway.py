"""Gateway permissions and store operations with a stubbed verifier."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

from pharos.core import FactGraph, GlobalMemory
from pharos.gateway import build_app, tools_for
from pharos.gateway import server
from pharos.tests.util import env as _env


@contextmanager
def _mock_verify(verdict, repair_hints="", raise_exc=None):
    """Replace server._verify with a stub; restore after."""
    orig = server._verify

    def fake(statement, proof):
        if raise_exc is not None:
            raise raise_exc
        return {"verdict": verdict, "repair_hints": repair_hints,
                "verification_report": {"summary": "mock"}, "run_id": "RID"}

    server._verify = fake
    try:
        yield
    finally:
        server._verify = orig


def test_role_table():
    assert "fact_submit" not in tools_for("main")
    assert "fact_revoke" in tools_for("main")
    assert tools_for("verifier") == ["search_arxiv_theorems"]
    assert "fact_submit" in tools_for("worker")
    for r in ("worker", "main", "verifier"):
        assert "search_arxiv_theorems" in tools_for(r)
    # Invalid roles must not gain write access.
    assert tools_for("nope") == tools_for("verifier")
    assert "fact_submit" not in tools_for("nope") and "gm_add" not in tools_for("nope")
    for r in ("worker", "main", "verifier", "all"):
        assert build_app(r) is not None


def test_gm_and_fact_search_over_temp_project():
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="tester"
    ):
        out = server.gm_add("plan", claim="reduce to q>=2", evidence="")
        assert out["kind"] == "plan" and out["id"]
        hits = server.gm_search("reduce")
        assert hits["counts_by_kind"] == {"plan": 1}
        hit = hits["results"][0]
        assert hit["id"] == out["id"] and hit["kind"] == "plan" and "entry" not in hit
        # the full entry comes from gm_get, one id at a time
        assert server.gm_get(out["id"])["entry"]["claim"] == "reduce to q>=2"
        assert server.gm_get("nope")["entry"] is None
        server.gm_add("proof_attempt", claim="long one", evidence="x" * 2000)
        assert server.gm_search("long")["results"][0]["evidence"].endswith("…")
        # one ranked list across kinds, capped by limit
        server.gm_add("dead_end", claim="reduce fails for q=1", evidence="")
        both = server.gm_search("reduce")
        assert {h["kind"] for h in both["results"]} == {"plan", "dead_end"}
        assert len(server.gm_search("reduce", limit=1)["results"]) == 1
        # fact_search over an empty graph is well-formed
        assert server.fact_search("anything")["results"] == []


def test_fact_search_dedupes_within_session_and_fact_get():
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="tester"
    ):
        fid = FactGraph(Path(d)).add(problem_id="p", author="w", statement="Every widget is blue.",
                                     proof="By the widget lemma.", predecessors=[],
                                     glossary_introduces={"widget": "a blue thing"})
        first = server.fact_search("widget")["results"][0]
        assert first["fact_id"] == fid and first["statement"] == "Every widget is blue."
        again = server.fact_search("widget")["results"][0]
        assert again == {"fact_id": fid, "score": first["score"], "seen": True}
        got = server.fact_get(fid)
        assert got["statement"] == "Every widget is blue." and "proof" not in got
        assert got["glossary_introduces"] == {"widget": "a blue thing"}
        assert server.fact_get(fid, with_proof=True)["proof"] == "By the widget lemma."
        assert "error" in server.fact_get("nope")


def test_fact_submit_accept_writes_fact_and_traces():
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="worker_xhigh",
        PHAROS_VERIFY_URL="http://mock", PHAROS_PROBLEM_ID="P",
    ), _mock_verify("correct"):
        res = server.fact_submit(statement="S(n)=n^2", proof="induction; QED")
        assert res["accepted"] is True and res["fact_id"]
        assert res["verify_log"] == str(Path(d) / "verifier" / "runs" / "RID" / "log.md")
        fg = FactGraph(Path(d))
        assert fg.exists(res["fact_id"])
        gm = GlobalMemory(Path(d))
        traces = gm.read("verification")
        assert traces and traces[-1]["verdict"] == "correct"
        assert traces[-1]["fact_id"] == res["fact_id"]


def test_fact_get_preserves_internal_statement_and_proof_headings(tmp_path):
    statement = "Assume X.\n\n## Conclusion\nThen Y."
    proof = "Begin.\n\n## Argument\nFinish."
    with _env(PHAROS_PROJECT_DIR=str(tmp_path), PHAROS_AGENTS_ROOT=None):
        graph = FactGraph(tmp_path)
        fid = graph.add(problem_id="p", author="w", statement=statement,
                        proof=proof, intuition="An explanation.")
        assert server.fact_get(fid)["statement"] == statement
        assert "proof" not in server.fact_get(fid)
        assert server.fact_get(fid, with_proof=True)["proof"] == proof
        assert graph.search("Conclusion")[0]["statement"] == "Assume X. ## Conclusion Then Y."


def test_fact_submit_reject_writes_nothing_but_traces():
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="worker_xhigh",
        PHAROS_VERIFY_URL="http://mock", PHAROS_PROBLEM_ID="P",
    ), _mock_verify("wrong", repair_hints="gap in step 2"):
        res = server.fact_submit(statement="bad", proof="hand-wave")
        assert res["accepted"] is False and res["repair_hints"] == "gap in step 2"
        fg = FactGraph(Path(d))
        assert fg.list() == []  # nothing written
        gm = GlobalMemory(Path(d))
        assert gm.read("verification")[-1]["verdict"] == "wrong"  # but traced


def test_fact_submit_verify_error_is_clean():
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="w",
        PHAROS_VERIFY_URL="http://mock", PHAROS_PROBLEM_ID="P",
    ), _mock_verify("correct", raise_exc=RuntimeError("service down")):
        res = server.fact_submit(statement="s", proof="p")
        assert res["accepted"] is False and res["verdict"] == "error"
        assert "service down" in res["error"]


def test_fact_submit_accept_but_write_failed_still_traces():
    # a revoked predecessor makes FactGraph.add raise; the verdict is still traced
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="worker_xhigh",
        PHAROS_VERIFY_URL="http://mock", PHAROS_PROBLEM_ID="P",
    ), _mock_verify("correct"):
        fg = FactGraph(Path(d))
        base = fg.add(problem_id="P", author="w", statement="A holds", proof="pf A")
        fg.revoke(base, reason="A was wrong")
        res = server.fact_submit(statement="B from A", proof="uses A", predecessors=[base])
        assert res["accepted"] is True and res["fact_id"] is None and res["write_error"]
        assert GlobalMemory(Path(d)).read("verification")[-1]["verdict"] == "correct"


def test_fact_submit_nondict_verify_body_is_clean():
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="w",
        PHAROS_VERIFY_URL="http://mock", PHAROS_PROBLEM_ID="P",
    ):
        orig = server._verify
        server._verify = lambda statement, proof: ["not", "a", "dict"]
        try:
            res = server.fact_submit(statement="s", proof="p")
            assert res["accepted"] is False and res["verdict"] == "error"
            assert "non-dict" in res["error"]
            assert FactGraph(Path(d)).list() == []  # nothing written
        finally:
            server._verify = orig


def test_project_by_name_without_agents_root_raises():
    with _env(PHAROS_AGENTS_ROOT=None, PHAROS_PROJECT_DIR="/tmp/whatever"):
        try:
            server._project("proj_a")
            assert False, "should require PHAROS_AGENTS_ROOT to resolve by name"
        except RuntimeError as e:
            assert "PHAROS_AGENTS_ROOT" in str(e)


def test_verify_http_roundtrip_and_errors():
    import http.server
    import threading

    captured = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            captured["body"] = self.rfile.read(n).decode("utf-8")
            captured["ctype"] = self.headers.get("Content-Type")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"verdict": "correct", "verification_report": {"ok": true}}')

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/verify"
    try:
        # not set -> RuntimeError
        with _env(PHAROS_VERIFY_URL=None):
            try:
                server._verify("s", "p")
                assert False, "should raise when PHAROS_VERIFY_URL unset"
            except RuntimeError as e:
                assert "PHAROS_VERIFY_URL" in str(e)
        # a real POST round-trip; the body is the JSON we sent
        with _env(PHAROS_VERIFY_URL=url, PHAROS_VERIFY_TIMEOUT="5"):
            out = server._verify("S(n)=n^2", "induction")
            assert out["verdict"] == "correct"
        assert '"statement": "S(n)=n^2"' in captured["body"]
        assert captured["ctype"] == "application/json"
        # a garbage timeout falls back to the default (no crash)
        with _env(PHAROS_VERIFY_URL=url, PHAROS_VERIFY_TIMEOUT="not-an-int"):
            assert server._verify("s", "p")["verdict"] == "correct"
    finally:
        srv.shutdown()


def test_fact_revoke_cascades():
    with tempfile.TemporaryDirectory() as d, _env(
        PHAROS_PROJECT_DIR=d, PHAROS_AGENTS_ROOT=None, PHAROS_AUTHOR="main_agent",
    ):
        fg = FactGraph(Path(d))
        base = fg.add(problem_id="P", author="w", statement="A holds", proof="pf A")
        child = fg.add(problem_id="P", author="w", statement="B from A", proof="uses A",
                       predecessors=[base])
        # step 1: a dry run lists the cascade with statements and deletes nothing
        dry = server.fact_revoke(base, reason="A was wrong")
        assert dry["confirm"] is False and dry["count"] == 2
        assert {r["fact_id"] for r in dry["would_revoke"]} == {base, child}
        assert fg.exists(base) and fg.exists(child)
        # step 2: confirmed -> the cascade goes
        out = server.fact_revoke(base, reason="A was wrong", confirm=True)
        assert set(out["revoked"]) == {base, child}
        assert not fg.exists(base) and not fg.exists(child)
        assert "error" in server.fact_revoke("nope", reason="x")


def test_search_arxiv_theorems_delegates():
    orig = server._arxiv_search
    server._arxiv_search = lambda query, num_results=10: {
        "query": query, "num_results": num_results, "results": [{"title": "T"}]}
    try:
        out = server.search_arxiv_theorems("Beatty sequence", num_results=3)
        assert out["query"] == "Beatty sequence" and out["num_results"] == 3
        assert out["results"] == [{"title": "T"}]
    finally:
        server._arxiv_search = orig


def test_project_resolution_by_name_and_validation():
    with tempfile.TemporaryDirectory() as root:
        (Path(root) / "proj_a").mkdir()
        with _env(PHAROS_AGENTS_ROOT=root, PHAROS_PROJECT_DIR=None, PHAROS_AUTHOR="main_agent"):
            # main addresses a project by name
            out = server.gm_add("plan", claim="try route X", evidence="", project="proj_a")
            assert out["id"]
            assert GlobalMemory(Path(root) / "proj_a").read("plan")
            # path-escape / bad names are rejected
            for bad in ("../evil", "a/b", "", "/abs"):
                try:
                    server.gm_search("x", project=bad)
                    assert False, f"should reject project name {bad!r}"
                except RuntimeError:
                    pass
            # unknown project rejected
            try:
                server.gm_search("x", project="missing")
                assert False, "should reject unknown project"
            except RuntimeError:
                pass
