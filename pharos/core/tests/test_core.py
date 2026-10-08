"""Tests for fact storage, content addressing, revocation, and global memory."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pharos.core import (
    FactGraph,
    GlobalMemory,
    clean_external_refs,
    compute_fact_id,
    parse_frontmatter,
)
from pharos.core._util import read_jsonl


def test_global_memory_edge_cases():
    with tempfile.TemporaryDirectory() as d:
        gm = GlobalMemory(Path(d) / "p")
        try:
            gm.append("bogus_kind", claim="c", evidence="e", author="w")
            assert False, "should reject unknown kind"
        except ValueError:
            pass
        for i in range(3):
            gm.append("plan", claim=f"reduce to q>={i} case", evidence="", author="w")
        res = gm.search("reduce", kinds=["plan"], limit_per_kind=2)
        plan = res["results_by_kind"]["plan"]
        assert plan["count"] == 2
        assert gm.search("zzzquarkxyz", kinds=["plan"])["results_by_kind"]["plan"]["count"] == 0


def test_util_read_jsonl_missing_and_garbage():
    with tempfile.TemporaryDirectory() as d:
        missing = Path(d) / "nope.jsonl"
        assert read_jsonl(missing) == []
        garbage = Path(d) / "g.jsonl"
        garbage.write_text(
            '{"ok": 1}\n'          # valid dict
            "\n"                    # blank line skipped
            "not json at all\n"     # JSONDecodeError skipped
            "[1, 2, 3]\n"           # valid JSON but not a dict -> skipped
            '{"ok": 2}\n',
            encoding="utf-8",
        )
        rows = read_jsonl(garbage)
        assert rows == [{"ok": 1}, {"ok": 2}]


def test_global_memory():
    with tempfile.TemporaryDirectory() as d:
        gm = GlobalMemory(Path(d) / "project")

        # judgment (verifiable=false): no evidence required
        pid = gm.append("plan", claim="reduce to the q>=2 case", evidence="", author="worker_xhigh")
        assert [e for e in gm.read("plan") if e["id"] == pid][0]["status"] == "open"

        # a judgment with cited fact_ids in links (verifiable=false)
        eid = gm.append("direction", claim="prioritize the symplectic-rank route",
                        evidence="the rank obstruction is the crux", author="main_agent",
                        links={"fact_ids": ["abc123"]})
        eentry = [e for e in gm.read("direction") if e["id"] == eid][0]
        assert eentry["status"] == "open" and eentry["links"]["fact_ids"] == ["abc123"]

        # verification trace (logged by fact_submit; verifiable=false, extra fields allowed)
        vid = gm.append("verification", claim="Lemma L fails for n=2", evidence="verdict: correct",
                        author="worker_max", verdict="correct", fact_id="abc123")
        ventry = [e for e in gm.read("verification") if e["id"] == vid][0]
        assert ventry["verdict"] == "correct" and ventry["fact_id"] == "abc123"

        # verifiable kind with empty evidence is rejected
        try:
            gm.append("conclusion", claim="c", evidence="", author="w")
            assert False, "should require evidence"
        except ValueError:
            pass

        # a verifiable claim is written with status "unverified"
        gid = gm.append("counterexample", claim="Lemma L fails for n=2",
                        evidence="Take X=P^1; ... QED.", author="worker_max")
        assert [e for e in gm.read("counterexample") if e["id"] == gid][0]["status"] == "unverified"


def test_factgraph():
    with tempfile.TemporaryDirectory() as d:
        fg = FactGraph(Path(d) / "proj2")
        base = fg.add(problem_id="P", author="P_xhigh", statement="A holds", proof="proof of A",
                      glossary_introduces={"X": "a complex manifold"})
        child = fg.add(problem_id="P", author="P_xhigh", statement="B from A", proof="uses A",
                       predecessors=[base])
        grand = fg.add(problem_id="P", author="P_xhigh", statement="C from B", proof="uses B",
                       predecessors=[child])

        # content addressing: same content (incl. glossary) -> same id
        assert base == compute_fact_id(problem_id="P", predecessors=[],
                                       glossary_introduces={"X": "a complex manifold"},
                                       statement="A holds", proof="proof of A")
        assert fg.predecessors(child) == [base]
        assert set(fg.descendants(base)) == {child, grand}
        assert "## statement" in fg.get_raw(base) and "## proof" in fg.get_raw(base)

        # derived fact index: BM25 search over fact bodies, rebuilt on demand
        hits = fg.search("B from A")
        assert hits and hits[0]["fact_id"] == child
        assert hits[0]["statement"] == "B from A"          # snippet is the ## statement body
        assert all(h["score"] > 0 for h in hits)           # zero-score hits are dropped
        assert fg.search("nonexistent symplectic quark") == []

        # glossary: serialized in the node, merged into the project glossary, parsed back
        assert "X: a complex manifold" in fg.get_raw(base)
        assert fg.glossary().get("X") == "a complex manifold"
        assert parse_frontmatter(fg.get_raw(base))["glossary_introduces"] == {"X": "a complex manifold"}

        # cascade revoke + predecessor-revoked refusal
        revoked = fg.revoke(base, reason="A was wrong")
        assert set(revoked) == {base, child, grand}
        assert not fg.exists(base) and not fg.exists(child) and not fg.exists(grand)
        try:
            fg.add(problem_id="P", author="P_xhigh", statement="D from A", proof="uses A",
                   predecessors=[base])
            assert False, "should refuse revoked predecessor"
        except ValueError as e:
            assert "predecessor_revoked" in str(e)


def test_external_refs():
    with tempfile.TemporaryDirectory() as d:
        fg = FactGraph(Path(d) / "proj3")
        refs = [{"key": "HL26", "authors": ["Han", "Liu"], "title": "On X",
                 "arxiv": "2603.03817", "year": 2026, "cited_for": "Theorem 1.2"}]

        # Bibliography changes must preserve fact IDs and graph links.
        bare = compute_fact_id(problem_id="P", predecessors=[], glossary_introduces={},
                               statement="A holds", proof="proof of A")
        fid_a = fg.add(problem_id="P", author="w", statement="A holds", proof="proof of A",
                       external_refs=refs)
        assert fid_a == bare, "external_refs must not change the fact_id"

        assert fg.external_refs(fid_a) == refs
        assert parse_frontmatter(fg.get_raw(fid_a))["external_refs"] == refs
        assert "external_refs:" in fg.get_raw(fid_a)

        fid_a2 = fg.add(problem_id="P", author="w", statement="A holds", proof="proof of A")
        assert fid_a2 == fid_a

        fid_b = fg.add(problem_id="P", author="w", statement="B holds", proof="proof of B")
        assert fg.external_refs(fid_b) == []
        without_refs = ("---\nfact_id: deadbeefdeadbeef\nproblem_id: P\nauthor: w\n"
                  "predecessors: []\nglossary_introduces: {}\n---\n\n## statement\nx\n\n## proof\ny\n")
        assert parse_frontmatter(without_refs)["external_refs"] == []

        # Updating bibliography preserves the statement and proof.
        body_before = fg.get_raw(fid_b).split("## statement", 1)[1]
        out = fg.set_external_refs(fid_b, refs)
        assert out == refs and fg.external_refs(fid_b) == refs
        assert fg.exists(fid_b)
        assert fg.get_raw(fid_b).split("## statement", 1)[1] == body_before

        assert clean_external_refs([{"title": "T", "key": "K"}, "junk", 7]) == [{"key": "K", "title": "T"}]
        assert clean_external_refs(None) == [] and clean_external_refs([]) == []


def test_search_caches_track_appends_and_removals(tmp_path):
    """The in-process indexes are derived caches: a fact added, revoked, or a
    memory entry appended after the first search must show up on the next."""
    fg = FactGraph(tmp_path)
    a = fg.add(problem_id="p", author="w", statement="alpha bound holds", proof="pf")
    assert [r["fact_id"] for r in fg.search("alpha")] == [a]
    b = fg.add(problem_id="p", author="w", statement="alpha sharper bound", proof="pf2")
    assert {r["fact_id"] for r in fg.search("alpha")} == {a, b}
    fg.revoke(a, reason="wrong")
    assert [r["fact_id"] for r in fg.search("alpha")] == [b]
    gm = GlobalMemory(tmp_path)
    gm.append("plan", claim="try gamma route", evidence="", author="w")
    assert gm.search("gamma", kinds=["plan"])["results_by_kind"]["plan"]["count"] == 1
    gm.append("plan", claim="gamma route refined", evidence="", author="w")
    assert gm.search("gamma", kinds=["plan"])["results_by_kind"]["plan"]["count"] == 2
