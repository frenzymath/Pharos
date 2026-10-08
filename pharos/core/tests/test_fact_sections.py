"""Fact field boundaries must not discard internal Markdown headings."""

import pytest

from pharos.core.factgraph import parse_frontmatter, section_of, serialize_fact, statement_of
from pharos.core.schema import Fact


@pytest.mark.parametrize("statement,proof,intuition", [
    ("S", "P", ""),
    ("S", "P", "I"),
    ("## Hypotheses\nS\n## Conclusion\nT", "P", ""),
    ("S", "## Step 1\nP\n## Step 2\nQ", ""),
    ("S", "P\n## Last step\nQ", "I\n## Motivation\nR"),
    ("S", "# Title\nP\n### Substep\nQ", ""),
    ("S", "P\n## proof of a lemma\nQ\n## statement details\nR", ""),
    ("S", "P\n```text\n## nonreserved heading\n```\nQ", ""),
])
def test_fields_roundtrip_with_internal_headings(statement, proof, intuition):
    raw = serialize_fact(Fact(
        fact_id="fixture", problem_id="fixture", author="fixture",
        predecessors=["parent"], statement=statement, proof=proof,
        intuition=intuition, glossary_introduces={"term": "meaning"},
    ))
    assert section_of(raw, "statement") == statement
    assert section_of(raw, "proof") == proof
    assert section_of(raw, "intuition") == intuition
    assert section_of(raw, "missing") == ""
    assert parse_frontmatter(raw)["predecessors"] == ["parent"]


def test_field_delimiters_preserve_case_and_whitespace_compatibility():
    raw = "  ## STATEMENT  \n S \n ## PROOF \n P\n## Internal\nQ\n ## INTUITION \n I "
    assert section_of(raw, "statement") == "S"
    assert section_of(raw, "proof") == "P\n## Internal\nQ"
    assert section_of(raw, "intuition") == "I"


def test_statement_snippet_includes_internal_headings():
    raw = "## statement\nFirst.\n## Hypothesis\nLast.\n## proof\nP"
    assert statement_of(raw) == "First. ## Hypothesis Last."
